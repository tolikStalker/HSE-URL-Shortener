from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import Link
from app.models.user import User
from app.schemas.link import LinkCreate, LinkUpdate
from app.services.cache_service import CacheService
from app.services.link_service import LinkService


@pytest.fixture
def mock_db_session(mocker):
    session = mocker.AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_cache_service(mocker):
    cache = mocker.AsyncMock(spec=CacheService)
    return cache


@pytest.fixture
def link_service(mock_db_session, mock_cache_service):
    return LinkService(db=mock_db_session, cache=mock_cache_service)


@pytest.fixture
def sample_user():
    return User(id=1, username="testuser", email="test@example.com")


@pytest.fixture
def sample_link():
    return Link(
        id=1,
        short_code="short1",
        original_url="https://example.com/test",
        click_count=0,
        owner_id=1,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
class TestLinkService:
    async def test_create_link_no_custom_alias(
        self, link_service, mock_db_session, mock_cache_service, sample_user, mocker
    ):
        mocker.patch("app.services.link_service.generate_short_code", return_value="gen123")

        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        data = LinkCreate(original_url="https://example.com/test1")

        result = await link_service.create_link(data, user=sample_user)

        assert result.short_code == "gen123"
        assert result.original_url == "https://example.com/test1"
        assert result.owner_id == sample_user.id

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_cache_service.set_url.assert_called_once_with("gen123", "https://example.com/test1")

    async def test_create_link_with_custom_alias(
        self, link_service, mock_db_session, mock_cache_service, sample_user, mocker
    ):
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        data = LinkCreate(original_url="https://example.com/test2", custom_alias="myalias")

        result = await link_service.create_link(data, user=sample_user)

        assert result.short_code == "myalias"
        assert result.original_url == "https://example.com/test2"

        mock_db_session.add.assert_called_once()
        mock_cache_service.set_url.assert_called_once_with("myalias", "https://example.com/test2")

    async def test_create_link_with_custom_alias_conflict(
        self, link_service, mock_db_session, sample_user, mocker
    ):
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_db_session.execute.return_value = mock_result

        data = LinkCreate(original_url="https://example.com/test", custom_alias="myalias")

        with pytest.raises(HTTPException) as excinfo:
            await link_service.create_link(data, user=sample_user)

        assert excinfo.value.status_code == 409
        assert "Alias 'myalias' is already taken" in str(excinfo.value.detail)

    async def test_resolve_redirect_from_cache(
        self, link_service, mock_db_session, mock_cache_service
    ):
        mock_cache_service.get_url.return_value = "https://example.com/cached"

        result = await link_service.resolve_redirect("cached1")

        assert result == "https://example.com/cached"
        mock_db_session.execute.assert_called_once()
        mock_cache_service.delete_stats.assert_called_once_with("cached1")

    async def test_resolve_redirect_from_db(
        self, link_service, mock_db_session, mock_cache_service, sample_link, mocker
    ):
        mock_cache_service.get_url.return_value = None

        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_link
        mock_db_session.execute.return_value = mock_result

        result = await link_service.resolve_redirect("short1")

        assert result == sample_link.original_url
        assert sample_link.click_count == 1

        mock_db_session.flush.assert_called_once()
        mock_cache_service.set_url.assert_called_once_with("short1", sample_link.original_url)
        mock_cache_service.delete_stats.assert_called_once_with("short1")

    async def test_resolve_redirect_not_found(
        self, link_service, mock_db_session, mock_cache_service, mocker
    ):
        mock_cache_service.get_url.return_value = None

        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as excinfo:
            await link_service.resolve_redirect("notfound")

        assert excinfo.value.status_code == 404

    async def test_resolve_redirect_expired(
        self, link_service, mock_db_session, mock_cache_service, sample_link, mocker
    ):
        mock_cache_service.get_url.return_value = None

        sample_link.expires_at = datetime.now(UTC) - timedelta(days=1)

        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_link
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as excinfo:
            await link_service.resolve_redirect("short1")

        assert excinfo.value.status_code == 410

    async def test_get_stats_from_cache(self, link_service, mock_cache_service):
        stats_data = {"click_count": 5}
        mock_cache_service.get_stats.return_value = stats_data

        result = await link_service.get_stats("short1")

        assert result == stats_data

    async def test_get_stats_from_db(
        self, link_service, mock_db_session, mock_cache_service, sample_link, mocker
    ):
        mock_cache_service.get_stats.return_value = None

        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_link
        mock_db_session.execute.return_value = mock_result

        result = await link_service.get_stats("short1")

        assert result["short_code"] == sample_link.short_code
        assert result["click_count"] == sample_link.click_count
        mock_cache_service.set_stats.assert_called_once()

    async def test_update_link_success(
        self, link_service, mock_db_session, mock_cache_service, sample_user, sample_link, mocker
    ):
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_link
        mock_db_session.execute.return_value = mock_result

        update_data = LinkUpdate(original_url="https://example.com/updated")

        result = await link_service.update_link("short1", update_data, sample_user)

        assert result.original_url == "https://example.com/updated"
        mock_db_session.flush.assert_called_once()
        mock_cache_service.invalidate.assert_called_once_with("short1")

    async def test_update_link_forbidden(self, link_service, mock_db_session, sample_link, mocker):
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_link
        mock_db_session.execute.return_value = mock_result

        other_user = User(id=99, username="other", email="other@example.com")
        update_data = LinkUpdate(original_url="https://example.com/updated")

        with pytest.raises(HTTPException) as excinfo:
            await link_service.update_link("short1", update_data, other_user)

        assert excinfo.value.status_code == 403

    async def test_delete_link_success(
        self, link_service, mock_db_session, mock_cache_service, sample_user, sample_link, mocker
    ):
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_link
        mock_db_session.execute.return_value = mock_result

        await link_service.delete_link("short1", sample_user)

        mock_db_session.delete.assert_called_once_with(sample_link)
        mock_db_session.flush.assert_called_once()
        mock_cache_service.invalidate.assert_called_once_with("short1")

    async def test_generate_unique_code_exhausted(
        self, link_service, mock_db_session, mock_cache_service, sample_user, mocker
    ):
        mocker.patch("app.services.link_service.generate_short_code", return_value="taken1")
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = "some-existing-id"
        mock_db_session.execute.return_value = mock_result

        data = LinkCreate(original_url="https://example.com/test")

        with pytest.raises(HTTPException) as excinfo:
            await link_service.create_link(data, user=sample_user)

        assert excinfo.value.status_code == 503

    async def test_search_by_url(self, link_service, mock_db_session, sample_link, mocker):
        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_link]
        mock_db_session.execute.return_value = mock_result

        res = await link_service.search_by_url("https://example.com/search-me")

        assert len(res) == 1
        assert res[0].original_url == "https://example.com/test"


@pytest.mark.asyncio
async def test_link_create_schema_past_date():
    past_date = datetime.now(UTC) - timedelta(days=1)

    with pytest.raises(ValidationError) as exc:
        LinkCreate(original_url="https://example.com", expires_at=past_date)

    assert "expires_at must be in the future" in str(exc.value)
