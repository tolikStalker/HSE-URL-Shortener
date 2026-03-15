import contextlib

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import database as db_module
from app.auth.dependencies import _resolve_user, get_current_user, get_optional_user
from app.database import get_db
from app.redis import close_redis, get_redis, init_redis, redis_manager


@pytest.mark.asyncio
async def test_get_db_commits_on_success(test_db_engine, mocker):
    original_factory = db_module.async_session_factory
    db_module.async_session_factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    try:
        gen = get_db()
        session = await gen.__anext__()
        assert session is not None
        mocker.patch.object(session, "commit", new_callable=mocker.AsyncMock)
        with contextlib.suppress(StopAsyncIteration):
            await gen.__anext__()
        session.commit.assert_called_once()
    finally:
        db_module.async_session_factory = original_factory


@pytest.mark.asyncio
async def test_get_db_rollback_on_exception(test_db_engine, mocker):
    original_factory = db_module.async_session_factory
    db_module.async_session_factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    try:
        gen = get_db()
        session = await gen.__anext__()
        mocker.patch.object(session, "rollback", new_callable=mocker.AsyncMock)
        with pytest.raises(RuntimeError, match="test rollback"):
            await gen.athrow(RuntimeError("test rollback"))
        session.rollback.assert_called_once()
    finally:
        db_module.async_session_factory = original_factory


@pytest.mark.asyncio
async def test_redis_manager_lifecycle():
    await init_redis()
    assert redis_manager._client is not None
    client = redis_manager.client
    assert client is not None

    async for redis_instance in get_redis():
        assert redis_instance == client
        break

    await close_redis()
    assert redis_manager._client is None

    with pytest.raises(RuntimeError):
        _ = redis_manager.client


@pytest.mark.asyncio
async def test_resolve_user_invalid_token(mocker):
    mock_db = mocker.AsyncMock(spec=AsyncSession)
    res = await _resolve_user("invalid.token.here", mock_db)
    assert res is None


@pytest.mark.asyncio
async def test_resolve_user_no_sub(mocker):
    mocker.patch("app.auth.dependencies.decode_access_token", return_value={"other": "data"})
    mock_db = mocker.AsyncMock(spec=AsyncSession)
    res = await _resolve_user("valid.token.no.sub", mock_db)
    assert res is None


@pytest.mark.asyncio
async def test_resolve_user_invalid_uuid(mocker):
    mocker.patch("app.auth.dependencies.decode_access_token", return_value={"sub": "not-a-uuid"})
    mock_db = mocker.AsyncMock(spec=AsyncSession)
    res = await _resolve_user("valid.token.bad.payload", mock_db)
    assert res is None


@pytest.mark.asyncio
async def test_get_current_user_fails_on_invalid_token(mocker):
    mocker.patch("app.auth.dependencies._resolve_user", return_value=None)
    mock_db = mocker.AsyncMock(spec=AsyncSession)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad")

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds, mock_db)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_optional_user_none_credentials(mocker):
    mock_db = mocker.AsyncMock(spec=AsyncSession)
    res = await get_optional_user(None, mock_db)
    assert res is None
