from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis import get_redis
from app.services.cache_service import CacheService
from app.services.link_service import LinkService

router = APIRouter(tags=["Redirect"])


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    redis: Redis = Depends(get_redis),  # noqa: B008
):
    """Redirect to the original URL by short code."""
    service = LinkService(db, CacheService(redis))
    original_url = await service.resolve_redirect(short_code)
    return RedirectResponse(url=original_url, status_code=307)
