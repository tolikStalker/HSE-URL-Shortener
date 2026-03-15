from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.link import Link
from app.services.cache_service import CacheService
from app.services.cleanup_service import cleanup_expired_links, cleanup_unused_links


@pytest.mark.unit
class TestCleanupService:
    @pytest.mark.asyncio
    async def test_cleanup_expired_links(self, test_session, mocker):
        expired_link = Link(
            short_code="expired",
            original_url="https://example.com",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        test_session.add(expired_link)
        await test_session.flush()

        active_link = Link(
            short_code="active",
            original_url="https://example.com",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        test_session.add(active_link)
        await test_session.flush()

        mock_cache_service = mocker.AsyncMock(spec=CacheService)

        await cleanup_expired_links(test_session, mock_cache_service)

        remaining = await test_session.execute(select(Link))
        remaining_links = remaining.scalars().all()
        assert len(remaining_links) == 1
        assert remaining_links[0].short_code == "active"

    @pytest.mark.asyncio
    async def test_cleanup_unused_links(self, test_session, mocker):
        old_link = Link(
            short_code="old",
            original_url="https://example.com",
            created_at=datetime.now(UTC) - timedelta(days=40),
            last_used_at=None,
        )
        test_session.add(old_link)
        await test_session.flush()

        recent_link = Link(
            short_code="recent",
            original_url="https://example.com",
            created_at=datetime.now(UTC) - timedelta(days=5),
            last_used_at=None,
        )
        test_session.add(recent_link)
        await test_session.flush()

        mock_cache_service = mocker.AsyncMock(spec=CacheService)

        await cleanup_unused_links(test_session, mock_cache_service)

        remaining = await test_session.execute(select(Link))
        remaining_links = remaining.scalars().all()
        assert len(remaining_links) == 1
        assert remaining_links[0].short_code == "recent"

    @pytest.mark.asyncio
    async def test_cleanup_expired_links_empty(self, test_session, mocker):
        mock_cache_service = mocker.AsyncMock(spec=CacheService)

        result = await cleanup_expired_links(test_session, mock_cache_service)

        assert result == 0
        mock_cache_service.invalidate.assert_not_called()
