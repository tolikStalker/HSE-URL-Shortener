from fastapi import APIRouter, Depends, Path
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
    short_code: str = Path(..., pattern=r"^[a-zA-Z0-9_-]{3,20}$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),  # noqa: B008
):
    service = LinkService(db, CacheService(redis))
    original_url = await service.resolve_redirect(short_code)
    return RedirectResponse(url=original_url, status_code=302)
