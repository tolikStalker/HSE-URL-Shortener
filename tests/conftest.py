from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base
from app.redis import get_redis

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession]:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture
def override_get_db(test_session):
    async def _override_get_db():
        try:
            yield test_session
            await test_session.commit()
        except Exception:
            await test_session.rollback()
            raise

    return _override_get_db


@pytest.fixture
async def mock_redis(mocker):
    mock_redis_client = mocker.AsyncMock()
    mock_redis_client.get = mocker.AsyncMock(return_value=None)
    mock_redis_client.set = mocker.AsyncMock()
    mock_redis_client.delete = mocker.AsyncMock()
    mock_redis_client.close = mocker.AsyncMock()
    return mock_redis_client


@pytest.fixture
def override_get_redis(mock_redis):
    async def _override_get_redis():
        yield mock_redis

    return _override_get_redis


@pytest.fixture
def app_with_overrides(override_get_db, override_get_redis):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    return app


@pytest.fixture
async def client(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
