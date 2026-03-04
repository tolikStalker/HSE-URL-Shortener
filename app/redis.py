from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.config import settings

redis_client: Redis | None = None


async def init_redis() -> None:
    global redis_client
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_redis() -> AsyncGenerator[Redis]:
    if redis_client is None:
        raise RuntimeError("Redis is not initialized")
    yield redis_client
