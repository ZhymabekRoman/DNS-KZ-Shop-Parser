from loguru import logger
from validators import url


async def safe_check_redis_connection(connection):
    try:
        response = await connection.ping()
    except Exception as e:
        logger.error(f"Error while checking redis connection: {e}")
        return False
    else:
        return response
    

def verify_link(link):
    if not (verify_link := url(link)):
        logger.error(f"Invalid link: {link}")
        exit(1)
    return verify_link


def increment_page(page_url: str):
    pass