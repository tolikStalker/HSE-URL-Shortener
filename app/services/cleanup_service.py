import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.link import Link
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


async def _delete_links_and_invalidate(
    db: AsyncSession,
    cache: CacheService,
    *where_clauses: Any,
    label: str,
) -> int:
    result = await db.execute(delete(Link).where(*where_clauses).returning(Link.short_code))
    codes = [row[0] for row in result.all()]

    if not codes:
        return 0

    for code in codes:
        await cache.invalidate(code)

    logger.info("Cleaned up %d %s links", len(codes), label)
    return len(codes)


async def cleanup_expired_links(db: AsyncSession, cache: CacheService) -> int:
    now = datetime.now(UTC)
    return await _delete_links_and_invalidate(
        db,
        cache,
        Link.expires_at.isnot(None),
        Link.expires_at < now,
        label="expired",
    )


async def cleanup_unused_links(db: AsyncSession, cache: CacheService) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.cleanup_unused_days)
    return await _delete_links_and_invalidate(
        db,
        cache,
        (
            ((Link.last_used_at.is_(None)) & (Link.created_at < cutoff))
            | ((Link.last_used_at.isnot(None)) & (Link.last_used_at < cutoff))
        ),
        label="unused",
    )
