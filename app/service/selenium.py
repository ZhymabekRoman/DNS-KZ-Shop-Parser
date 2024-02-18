from selenium import webdriver

def get_browser() -> webdriver.Chrome:
    local_state = {
        "dns_over_https.mode": "secure",
        "dns_over_https.templates": "https://dns.nextdns.io/db7d78",
        # "dns_over_https.templates": "https://dns.google/dns-query{?dns}",
        # "dns_over_https.templates": "https://chrome.cloudflare-dns.com/dns-query",
    }
    
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    # options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--single-process")
    options.add_experimental_option("localState", local_state)
    
    browser = webdriver.Chrome(options=options)
    return browser