import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.link import Link
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


async def cleanup_expired_links(db: AsyncSession, cache: CacheService) -> int:
    now = datetime.now(UTC)

    result = await db.execute(
        delete(Link)
        .where(Link.expires_at.isnot(None), Link.expires_at < now)
        .returning(Link.short_code)
    )
    expired_codes = [row[0] for row in result.all()]

    if not expired_codes:
        return 0

    await db.commit()

    for code in expired_codes:
        await cache.invalidate(code)

    logger.info("Cleaned up %d expired links", len(expired_codes))
    return len(expired_codes)


async def cleanup_unused_links(db: AsyncSession, cache: CacheService) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.cleanup_unused_days)

    result = await db.execute(
        delete(Link)
        .where(
            ((Link.last_used_at.is_(None)) & (Link.created_at < cutoff))
            | ((Link.last_used_at.isnot(None)) & (Link.last_used_at < cutoff))
        )
        .returning(Link.short_code)
    )
    unused_codes = [row[0] for row in result.all()]

    if not unused_codes:
        return 0

    await db.commit()

    for code in unused_codes:
        await cache.invalidate(code)

    logger.info("Cleaned up %d unused links", len(unused_codes))
    return len(unused_codes)
