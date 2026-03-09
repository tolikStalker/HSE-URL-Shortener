from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.config import settings


class RedisManager:
    def __init__(self) -> None:
        self._client: Redis | None = None

    async def init(self) -> None:
        self._client = Redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis is not initialized")
        return self._client


redis_manager = RedisManager()


async def init_redis() -> None:
    await redis_manager.init()


async def close_redis() -> None:
    await redis_manager.close()


async def get_redis() -> AsyncGenerator[Redis]:
    yield redis_manager.client
