from redis.asyncio import Redis

redis_storage = Redis(host="localhost", port=6379, db=0)