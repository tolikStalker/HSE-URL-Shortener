from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_optional_user
from app.dependencies import DbSession, RedisClient
from app.models.link import Link
from app.models.user import User
from app.schemas.link import LinkCreate, LinkResponse, LinkStats, LinkUpdate
from app.services.cache_service import CacheService
from app.services.link_service import LinkService

router = APIRouter(prefix="/links", tags=["Links"])

CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
OriginalUrl = Annotated[str, Query(...)]


def _get_service(db: AsyncSession, redis: Redis) -> LinkService:
    return LinkService(db, CacheService(redis))


def _to_response(link: Link) -> LinkResponse:
    return LinkResponse(
        id=link.id,
        short_code=link.short_code,
        short_url=link.short_url,
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


@router.post("/shorten", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_short_link(
    data: LinkCreate,
    db: DbSession,
    redis: RedisClient,
    user: OptionalUser,
):
    service = _get_service(db, redis)
    link = await service.create_link(data, user)
    return _to_response(link)


@router.get("/search", response_model=list[LinkResponse])
async def search_by_original_url(
    original_url: OriginalUrl,
    db: DbSession,
    redis: RedisClient,
):
    service = _get_service(db, redis)
    links = await service.search_by_url(original_url)
    return [_to_response(link) for link in links]


@router.get("/{short_code}/stats", response_model=LinkStats)
async def get_link_stats(
    short_code: str,
    db: DbSession,
    redis: RedisClient,
):
    service = _get_service(db, redis)
    return await service.get_stats(short_code)


@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code: str,
    data: LinkUpdate,
    db: DbSession,
    redis: RedisClient,
    user: CurrentUser,
):
    service = _get_service(db, redis)
    link = await service.update_link(short_code, data, user)
    return _to_response(link)


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    short_code: str,
    db: DbSession,
    redis: RedisClient,
    user: CurrentUser,
):
    service = _get_service(db, redis)
    await service.delete_link(short_code, user)
