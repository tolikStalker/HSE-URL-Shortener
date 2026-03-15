import json

import pytest

from app.services.cache_service import CacheService


@pytest.mark.unit
class TestCacheService:
    @pytest.fixture
    def cache_service(self, mock_redis):
        return CacheService(mock_redis)

    @pytest.mark.asyncio
    async def test_set_url(self, cache_service, mock_redis):
        short_code = "abc123"
        url = "https://example.com"

        await cache_service.set_url(short_code, url)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == f"link:{short_code}"
        assert call_args[0][1] == url
        assert call_args[1]["ex"] == cache_service.ttl

    @pytest.mark.asyncio
    async def test_get_url(self, cache_service, mock_redis):
        short_code = "abc123"
        url = "https://example.com"
        mock_redis.get.return_value = url

        result = await cache_service.get_url(short_code)

        assert result == url
        mock_redis.get.assert_called_once_with(f"link:{short_code}")

    @pytest.mark.asyncio
    async def test_get_url_not_found(self, cache_service, mock_redis):
        mock_redis.get.return_value = None

        result = await cache_service.get_url("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_stats(self, cache_service, mock_redis):
        short_code = "abc123"
        stats = {"clicks": 10, "created_at": "2024-01-01"}

        await cache_service.set_stats(short_code, stats)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == f"stats:{short_code}"
        assert json.loads(call_args[0][1]) == stats

    @pytest.mark.asyncio
    async def test_get_stats(self, cache_service, mock_redis):
        short_code = "abc123"
        stats = {"clicks": 10}
        mock_redis.get.return_value = json.dumps(stats)

        result = await cache_service.get_stats(short_code)

        assert result == stats

    @pytest.mark.asyncio
    async def test_delete_stats(self, cache_service, mock_redis):
        short_code = "abc123"

        await cache_service.delete_stats(short_code)

        mock_redis.delete.assert_called_once_with(f"stats:{short_code}")

    @pytest.mark.asyncio
    async def test_invalidate(self, cache_service, mock_redis):
        short_code = "abc123"

        await cache_service.invalidate(short_code)

        mock_redis.delete.assert_called_once_with(
            f"link:{short_code}",
            f"stats:{short_code}",
        )
