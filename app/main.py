import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.router import api_router
from app.database import async_session_factory, engine
from app.redis import close_redis, get_redis, init_redis
from app.services.cache_service import CacheService
from app.services.cleanup_service import cleanup_expired_links, cleanup_unused_links

logger = logging.getLogger(__name__)


async def periodic_cleanup(interval_seconds: int = 600) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with async_session_factory() as db:
                async for redis in get_redis():
                    cache = CacheService(redis)
                    expired = await cleanup_expired_links(db, cache)
                    unused = await cleanup_unused_links(db, cache)
                    if expired or unused:
                        logger.info("Cleanup: %d expired, %d unused links removed", expired, unused)
        except Exception:
            logger.exception("Error during periodic cleanup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()

    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task

    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="URL Shortener",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


app.include_router(api_router)
