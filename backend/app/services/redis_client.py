import redis.asyncio as redis
from app.core.config import settings

class RedisService:
    _request_client: redis.Redis | None = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        if cls._request_client is None:
            cls._request_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
        return cls._request_client

    @classmethod
    async def close(cls):
        if cls._request_client:
            await cls._request_client.close()
            cls._request_client = None

async def get_redis() -> redis.Redis:
    return RedisService.get_client()
