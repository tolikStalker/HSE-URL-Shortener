import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.link import Link


@pytest.mark.integration
class TestRedirectEndpoints:
    @pytest.mark.asyncio
    async def test_redirect_increments_click_count(self, client: AsyncClient):
        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/original",
            },
        )

        short_code = create_response.json()["short_code"]

        stats_before = await client.get(f"/links/{short_code}/stats")
        clicks_before = stats_before.json()["click_count"]

        await client.get(f"/{short_code}", follow_redirects=False)
        stats_after = await client.get(f"/links/{short_code}/stats")
        clicks_after = stats_after.json()["click_count"]

        assert clicks_after > clicks_before

    @pytest.mark.asyncio
    async def test_redirect_updates_last_used_at(self, client: AsyncClient):
        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/original",
            },
        )

        short_code = create_response.json()["short_code"]

        await client.get(f"/{short_code}", follow_redirects=False)
        stats_after = await client.get(f"/links/{short_code}/stats")
        last_used_after = stats_after.json().get("last_used_at")

        assert last_used_after is not None

    @pytest.mark.asyncio
    async def test_redirect_updates_last_used_at_on_repeat(self, client: AsyncClient, test_session):
        short_code = uuid.uuid4().hex[:8]
        fresh_link = Link(
            short_code=short_code,
            original_url="https://example.com/repeat-visit",
            click_count=0,
            last_used_at=datetime.now(UTC) - timedelta(seconds=5),
        )
        test_session.add(fresh_link)
        await test_session.commit()

        stats_before = await client.get(f"/links/{short_code}/stats")
        last_used_before = stats_before.json().get("last_used_at")
        assert last_used_before is not None

        await client.get(f"/{short_code}", follow_redirects=False)
        stats_after = await client.get(f"/links/{short_code}/stats")
        last_used_after = stats_after.json().get("last_used_at")

        assert last_used_after >= last_used_before

    @pytest.mark.asyncio
    async def test_redirect_with_expired_link(self, client: AsyncClient, test_session):
        short_code = uuid.uuid4().hex[:8]
        expired_link = Link(
            short_code=short_code,
            original_url="https://example.com/original",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        test_session.add(expired_link)
        await test_session.commit()

        response = await client.get(f"/{short_code}", follow_redirects=False)
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_redirect_without_last_used_at(self, client: AsyncClient, test_session):
        short_code = uuid.uuid4().hex[:8]
        link_without_used = Link(
            short_code=short_code, original_url="https://example.com/unused", click_count=0
        )
        test_session.add(link_without_used)
        await test_session.commit()

        response = await client.get(f"/{short_code}", follow_redirects=False)
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_redirect_updates_last_used_at_twice(self, client: AsyncClient):
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/double-visit"},
        )
        short_code = create_response.json()["short_code"]

        await client.get(f"/{short_code}", follow_redirects=False)

        stats_before = await client.get(f"/links/{short_code}/stats")
        last_used_before = stats_before.json().get("last_used_at")
        await client.get(f"/{short_code}", follow_redirects=False)
        stats_after = await client.get(f"/links/{short_code}/stats")
        last_used_after = stats_after.json().get("last_used_at")

        assert last_used_before is not None
        assert last_used_after >= last_used_before
