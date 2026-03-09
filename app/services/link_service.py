from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import Link
from app.models.user import User
from app.schemas.link import LinkCreate, LinkUpdate
from app.services.cache_service import CacheService
from app.utils.short_code import generate_short_code

_MAX_CODE_ATTEMPTS = 10


class LinkService:
    def __init__(self, db: AsyncSession, cache: CacheService):
        self.db = db
        self.cache = cache

    async def create_link(self, data: LinkCreate, user: User | None = None) -> Link:
        original_url = str(data.original_url)

        if data.custom_alias:
            existing = await self.db.execute(
                select(Link).where(Link.short_code == data.custom_alias)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Alias '{data.custom_alias}' is already taken",
                )
            short_code = data.custom_alias
        else:
            short_code = await self._generate_unique_code()

        link = Link(
            short_code=short_code,
            original_url=original_url,
            expires_at=data.expires_at,
            owner_id=user.id if user else None,
        )
        self.db.add(link)
        await self.db.flush()

        await self.cache.set_url(short_code, original_url)

        return link

    async def resolve_redirect(self, short_code: str) -> str:
        cached = await self.cache.get_url(short_code)
        if cached:
            link = await self._get_link_or_404(short_code)
            self._check_expired(link)
            link.click_count += 1
            link.last_used_at = datetime.now(UTC)
            await self.db.flush()
            await self.cache.delete_stats(short_code)
            return cached

        link = await self._get_link_or_404(short_code)
        self._check_expired(link)

        link.click_count += 1
        link.last_used_at = datetime.now(UTC)
        await self.db.flush()

        await self.cache.set_url(short_code, link.original_url)
        await self.cache.delete_stats(short_code)

        return link.original_url

    async def get_stats(self, short_code: str) -> dict:
        cached = await self.cache.get_stats(short_code)
        if cached:
            return cached

        link = await self._get_link_or_404(short_code)

        stats = {
            "short_code": link.short_code,
            "original_url": link.original_url,
            "created_at": link.created_at.isoformat(),
            "last_used_at": link.last_used_at.isoformat() if link.last_used_at else None,
            "click_count": link.click_count,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None,
            "owner_id": str(link.owner_id) if link.owner_id else None,
        }

        await self.cache.set_stats(short_code, stats)
        return stats

    async def update_link(self, short_code: str, data: LinkUpdate, user: User) -> Link:
        link = await self._get_link_or_404(short_code)
        self._check_ownership(link, user)
        link.original_url = str(data.original_url)
        await self.db.flush()
        await self.cache.invalidate(short_code)

        return link

    async def delete_link(self, short_code: str, user: User) -> None:
        link = await self._get_link_or_404(short_code)
        self._check_ownership(link, user)
        await self.db.delete(link)
        await self.db.flush()
        await self.cache.invalidate(short_code)

    async def search_by_url(self, original_url: str) -> list[Link]:
        result = await self.db.execute(select(Link).where(Link.original_url == original_url))
        return list(result.scalars().all())

    # --- Private methods ---

    async def _generate_unique_code(self) -> str:
        for _ in range(_MAX_CODE_ATTEMPTS):
            short_code = generate_short_code()
            existing = await self.db.execute(select(Link.id).where(Link.short_code == short_code))
            if existing.scalar_one_or_none() is None:
                return short_code

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate a unique shortcode, please try again",
        )

    async def _get_link_or_404(self, short_code: str) -> Link:
        result = await self.db.execute(select(Link).where(Link.short_code == short_code))
        link = result.scalar_one_or_none()
        if link is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
        return link

    def _check_expired(self, link: Link) -> None:
        if link.expires_at and link.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link has expired")

    def _check_ownership(self, link: Link, user: User) -> None:
        if link.owner_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This link was created anonymously and cannot be modified",
            )
        if link.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this link",
            )
