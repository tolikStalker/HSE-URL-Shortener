import json

from redis.asyncio import Redis

from app.config import settings


class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = settings.cache_ttl

    def _key(self, short_code: str) -> str:
        return f"link:{short_code}"

    def _stats_key(self, short_code: str) -> str:
        return f"stats:{short_code}"

    async def get_url(self, short_code: str) -> str | None:
        return await self.redis.get(self._key(short_code))

    async def set_url(self, short_code: str, original_url: str) -> None:
        await self.redis.set(self._key(short_code), original_url, ex=self.ttl)

    async def delete_url(self, short_code: str) -> None:
        await self.redis.delete(self._key(short_code))

    async def get_stats(self, short_code: str) -> dict | None:
        data = await self.redis.get(self._stats_key(short_code))
        if data:
            return json.loads(data)
        return None

    async def set_stats(self, short_code: str, stats: dict) -> None:
        await self.redis.set(
            self._stats_key(short_code), json.dumps(stats, default=str), ex=self.ttl
        )

    async def delete_stats(self, short_code: str) -> None:
        await self.redis.delete(self._stats_key(short_code))

    async def invalidate(self, short_code: str) -> None:
        await self.redis.delete(self._key(short_code), self._stats_key(short_code))
