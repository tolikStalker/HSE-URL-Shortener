import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.main import app, lifespan, periodic_cleanup
from app.schemas.link import LinkCreate


@pytest.mark.unit
class TestMainApp:
    @pytest.mark.asyncio
    async def test_periodic_cleanup_success(self, mocker):
        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError()

        mocker.patch("app.main.asyncio.sleep", side_effect=mock_sleep)

        mock_db = mocker.AsyncMock()
        mock_session_factory = mocker.MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        mocker.patch("app.main.async_session_factory", new=mock_session_factory)

        mocker.patch("app.main.cleanup_expired_links", return_value=1)
        mocker.patch("app.main.cleanup_unused_links", return_value=2)
        mocker.patch("app.main.CacheService")
        mocker.patch("app.main.redis_manager", mocker.MagicMock())

        with pytest.raises(asyncio.CancelledError):
            await periodic_cleanup(interval_seconds=0)

        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_periodic_cleanup_exception_handling(self, mocker):
        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError()

        mocker.patch("app.main.asyncio.sleep", side_effect=mock_sleep)

        mock_session_factory = mocker.MagicMock()
        mock_session_factory.return_value.__aenter__.side_effect = Exception("DB error")
        mocker.patch("app.main.async_session_factory", new=mock_session_factory)

        with pytest.raises(asyncio.CancelledError):
            await periodic_cleanup(interval_seconds=0)

    @pytest.mark.asyncio
    async def test_lifespan(self, mocker):
        mock_init_redis = mocker.patch("app.main.init_redis", new_callable=mocker.AsyncMock)
        mock_close_redis = mocker.patch("app.main.close_redis", new_callable=mocker.AsyncMock)

        mock_engine = mocker.AsyncMock()
        mocker.patch("app.main.engine", new=mock_engine)

        async def mock_cleanup(*args, **kwargs):
            await asyncio.sleep(100)

        mocker.patch("app.main.periodic_cleanup", side_effect=mock_cleanup)

        async with lifespan(app):
            await asyncio.sleep(0)

        mock_init_redis.assert_called_once()
        mock_close_redis.assert_called_once()
        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_periodic_cleanup_logs_deletion(self, mocker):
        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError()

        mocker.patch("app.main.asyncio.sleep", side_effect=mock_sleep)

        mock_db = mocker.AsyncMock()
        mock_session_factory = mocker.MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        mocker.patch("app.main.async_session_factory", new=mock_session_factory)

        mocker.patch("app.main.cleanup_expired_links", return_value=5)
        mocker.patch("app.main.cleanup_unused_links", return_value=10)
        mocker.patch("app.main.CacheService")
        mocker.patch("app.main.redis_manager", mocker.MagicMock())
        mock_logger = mocker.patch("app.main.logger.info")

        with pytest.raises(asyncio.CancelledError):
            await periodic_cleanup(interval_seconds=0)

        mock_logger.assert_called_once_with("Cleanup: %d expired, %d unused links removed", 5, 10)


@pytest.mark.asyncio
async def test_link_create_schema_future_date():

    future_date = datetime.now(UTC) + timedelta(days=1)
    link = LinkCreate(original_url="https://example.com", expires_at=future_date)
    assert link.expires_at == future_date
