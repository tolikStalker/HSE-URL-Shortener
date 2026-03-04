import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.link import Link
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


async def cleanup_expired_links(db: AsyncSession, cache: CacheService) -> int:
    """Delete links past their expires_at time. Returns count of deleted links."""
    now = datetime.now(UTC)

    # Find expired links to invalidate cache
    result = await db.execute(
        select(Link.short_code).where(Link.expires_at.isnot(None), Link.expires_at < now)
    )
    expired_codes = [row[0] for row in result.all()]

    if not expired_codes:
        return 0

    # Delete from DB
    await db.execute(
        delete(Link).where(Link.expires_at.isnot(None), Link.expires_at < now)
    )
    await db.commit()

    # Invalidate cache
    for code in expired_codes:
        await cache.invalidate(code)

    logger.info("Cleaned up %d expired links", len(expired_codes))
    return len(expired_codes)


async def cleanup_unused_links(db: AsyncSession, cache: CacheService) -> int:
    """Delete links that haven't been used for CLEANUP_UNUSED_DAYS days."""
    cutoff = datetime.now(UTC) - timedelta(days=settings.cleanup_unused_days)

    # Find unused links
    result = await db.execute(
        select(Link.short_code).where(
            # Never used and created before cutoff
            ((Link.last_used_at.is_(None)) & (Link.created_at < cutoff))
            |
            # Last used before cutoff
            ((Link.last_used_at.isnot(None)) & (Link.last_used_at < cutoff))
        )
    )
    unused_codes = [row[0] for row in result.all()]

    if not unused_codes:
        return 0

    await db.execute(
        delete(Link).where(Link.short_code.in_(unused_codes))
    )
    await db.commit()

    for code in unused_codes:
        await cache.invalidate(code)

    logger.info("Cleaned up %d unused links", len(unused_codes))
    return len(unused_codes)
