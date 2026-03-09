from typing import Annotated

from fastapi import APIRouter, Path
from fastapi.responses import RedirectResponse

from app.dependencies import DbSession, RedisClient
from app.services.cache_service import CacheService
from app.services.link_service import LinkService

router = APIRouter(tags=["Redirect"])

ShortCode = Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{3,20}$")]


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: ShortCode,
    db: DbSession,
    redis: RedisClient,
):
    service = LinkService(db, CacheService(redis))
    original_url = await service.resolve_redirect(short_code)
    return RedirectResponse(url=original_url, status_code=302)
