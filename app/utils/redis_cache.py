import pickle
from functools import wraps
from loguru import logger

from app.utils import safe_check_redis_connection
from app.service import redis_storage

def redis_cache(expire_time: int = 60 * 10, ignore_args: list = []):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not await safe_check_redis_connection(redis_storage):
                logger.error("REDIS is not available!")
                return await func(*args, **kwargs)
            logger.trace(f"{expire_time=}")
            
            # Filter out ignored arguments by their index
            filtered_args = [arg for index, arg in enumerate(args) if index not in ignore_args]
            # Generate the key without the ignored arguments
            key = "{}-{}".format(func.__name__, ",".join(str(arg) for arg in filtered_args))
            
            logger.trace(f"REDIS key: {key}")
            result = await redis_storage.get(key)

            if result is not None:
                result_raw = pickle.loads(result)
                logger.trace("Result found in REDIS")
            else:
                logger.trace("Result not found in REDIS")
                result_raw = await func(*args, **kwargs)
                result = pickle.dumps(result_raw)
                await redis_storage.setex(key, expire_time, result)
                logger.trace("Value is now in Redis")

            return result_raw

        return wrapper

    return decorator