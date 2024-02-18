import os
import re
import asyncio
import json
from time import sleep
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from icecream import ic
from loguru import logger
from pydantic import BaseModel
from selenium.webdriver.support.ui import WebDriverWait

from app.service import get_browser
from app.utils import redis_cache, verify_link, increment_page
from app.exports import export_to_excel

URL_PREFIX = "https://www.dns-shop.kz/"

MAX_CONCURRENT_TASKS = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

@redis_cache(ignore_args=[0], expire_time=10 * 60 * 60)
async def get_page(browser, link: str):
    verify_link(link)

    logger.info(f"Requesting page: {link}")
    browser.get(link)

    WebDriverWait(browser, 150).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')

    sleep(5) # wait, until some extra data (like price) is loaded from API

    if "404" in browser.title:
        logger.error(f"Page not found: {link}")
        exit(1)

    page_source = browser.page_source

    return page_source

def parse_product(content: str) -> dict:
    soup = BeautifulSoup(content, 'html.parser')
    product_info = {}

    product_card = soup.find("div", class_="product-card-tabs__contents")
    product_groups = product_card.find_all(class_="product-characteristics__group")
    
    product_info['groups'] = []
    for group in product_groups:
        group_dict = {}
        group_title = group.find(class_="product-characteristics__group-title").text.strip()
        group_dict['title'] = group_title
        
        specs = group.find_all(class_="product-characteristics__spec")
        group_dict['specs'] = []
        for spec in specs:
            spec_dict = {}
            spec_title = spec.find(class_="product-characteristics__spec-title").text.strip()
            spec_value = spec.find(class_="product-characteristics__spec-value").text.strip()
            spec_dict['title'] = spec_title
            spec_dict['value'] = spec_value
            group_dict['specs'].append(spec_dict)
        
        product_info['groups'].append(group_dict)
    
    description_div = soup.find('div', class_='product-card-description-text')
    if description_div:
        description_paragraphs = description_div.find_all('p')
        description_text = ' '.join(paragraph.text for paragraph in description_paragraphs)
        product_info['description'] = description_text
    else:
        product_info['description'] = "Description not found."

    product_img_view_block = soup.find(class_="product-card-top__images")
    images = product_img_view_block.select('picture source')

    # Ignores thumb image, not a bug, but feature lol
    image_urls = [img['data-srcset'] for img in images if 'data-srcset' in img.attrs]
    product_info['image_links'] = image_urls
    
    return product_info
    

def parse_catalog(content: str):
    soup = BeautifulSoup(content, "html.parser")

    products_page_title = soup.find("div", class_="products-page__title")
    title = products_page_title.find("h1").text
    logger.info(f"Low category title: {title}")

    item_count_raw = products_page_title.find(
        "span", {"data-role": "items-count", "class": "products-count"}
    ).text
    item_count = re.match("\d+", item_count_raw).group()
    logger.info(f"Low category item count: {item_count}")

    products = soup.find_all("div", class_="catalog-product ui-button-widget")

    products_out = []
    for product in products:
        logger.trace(ic.format(product))
        name = product.find("a", class_="catalog-product__name").text.strip()

        product_buy = product.find("div", class_="catalog-product__buy")

        price_block = product_buy.find("div", class_="product-buy__price-wrap")
        price_element = price_block.find("div", class_="product-buy__price")
        if price_element:
            # TODO: Implement prev price. For now we just ignore that
            prev_price_span = price_element.find("span", class_="product-buy__prev")
            if prev_price_span:
                prev_price_span.decompose()

        if price_element:
            price = price_element.text.strip().replace("\xa0₸", " KZT")
        else:
            price = "Price not available"

        availability_element = product.find("div", class_="order-avail-wrap")
        if availability_element:
            availability = availability_element.text.strip()
            # availability = availability_element.find("span", class_="available").text
        else:
            availability = "Availability information not available"

        product_image_parrent = product.find("div", class_="catalog-product__image")
        product_link = product_image_parrent.find("a", class_="catalog-product__image-link").get("href")
        if product_link:
            product_image = product_image_parrent.find("img").get("data-src")

        logger.debug(f"Name: {name}\nPrice: {price}\nAvailability: {availability}\nLink: {product_link}\nThumb image: {product_image}\n---")

        products_out.append(
            {
                "name": name,
                "price": price,
                "availability": availability,
                "link": product_link,
                "thumb": product_image,
            }
        )

    return {
        "title": title,
        "item_count": item_count,
        "products": products_out
    }

async def main():
    with open(os.path.join(os.path.dirname(__file__), "../dns-links.txt")) as f:
        links = f.readlines()

    if not links:
        logger.error("No DNS shop links found in the file 'dns-links.txt'")
        exit(1)

    browser = get_browser()

    async def limited_get_page(browser, url):
        async with semaphore:
            return await get_page(browser, url)
    
    for link in links:
        logger.info(f"Parsing shop link: {link.strip()}")

        if not link.strip():
            logger.warning("Skipping empty link")
            continue

        link_content = await get_page(browser, link.strip())

        soup = BeautifulSoup(link_content, "html.parser")
        li_elements_with_data_page_number = soup.find_all('li', attrs={'data-page-number': True})

        max_page = max(li_elements_with_data_page_number, key=lambda li: int(li.get('data-page-number'))).get('data-page-number')
        logger.debug(f"Pages in this category: {max_page}")

        tasks = []
        for page_number in range(1, 2):
        # for page_number in range(1, int(max_page) + 1):
            params = {'page': page_number}
            full_url = urljoin(link.strip(), '?' + urlencode(params))
            logger.debug(f"Requesting page: {full_url}")
            task = asyncio.create_task(limited_get_page(browser, full_url))
            tasks.append(task)

        pages_content = await asyncio.gather(*tasks)

        result = []
        for link_content in pages_content:
            catalog_result = parse_catalog(link_content)
            for product_i, product in enumerate(catalog_result["products"]):
                product_content = await get_page(browser, urljoin(URL_PREFIX, f"{product['link']}characteristics/"))
                product_result = parse_product(product_content)
                catalog_result["products"][product_i]["extra"] = product_result
                # logger.debug(product_result)
            result.append(catalog_result)
        
            with open("catalog_result.json", "w") as file:
                json.dump(catalog_result, file, indent=4, ensure_ascii=False)
        
            export_to_excel("catalog_result.json", "exported_data.xlsx")
        
