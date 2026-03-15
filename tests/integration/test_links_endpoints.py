import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestLinksEndpoints:
    @pytest.fixture
    async def auth_token(self, client: AsyncClient):
        await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePassword123!",
            },
        )

        response = await client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "SecurePassword123!",
            },
        )

        return response.json()["access_token"]

    @pytest.mark.asyncio
    async def test_create_short_link_success(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/very/long/url",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert data["original_url"] == "https://example.com/very/long/url"

    @pytest.mark.asyncio
    async def test_create_short_link_with_custom_alias(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/very/long/url",
                "custom_alias": "mylink",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["short_code"] == "mylink"

    @pytest.mark.asyncio
    async def test_create_short_link_duplicate_alias(self, client: AsyncClient):
        await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/url1",
                "custom_alias": "mylink",
            },
        )

        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/url2",
                "custom_alias": "mylink",
            },
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_redirect_link(self, client: AsyncClient):
        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/original",
            },
        )

        short_code = create_response.json()["short_code"]

        response = await client.get(f"/{short_code}", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/original"

    @pytest.mark.asyncio
    async def test_redirect_nonexistent_link(self, client: AsyncClient):
        response = await client.get("/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_link_stats(self, client: AsyncClient):
        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/original",
            },
        )

        short_code = create_response.json()["short_code"]

        await client.get(f"/{short_code}", follow_redirects=False)
        await client.get(f"/{short_code}", follow_redirects=False)

        response = await client.get(f"/links/{short_code}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "click_count" in data
        assert data["click_count"] >= 2

    @pytest.mark.asyncio
    async def test_search_by_url(self, client: AsyncClient):
        original_url = "https://example.com/search-test"

        await client.post(
            "/links/shorten",
            json={
                "original_url": original_url,
            },
        )

        response = await client.get(f"/links/search?original_url={original_url}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["original_url"] == original_url

    @pytest.mark.asyncio
    async def test_delete_link_requires_auth(self, client: AsyncClient):
        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/original",
            },
        )

        short_code = create_response.json()["short_code"]

        response = await client.delete(f"/links/{short_code}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_link_requires_auth(self, client: AsyncClient):
        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/original",
            },
        )

        short_code = create_response.json()["short_code"]

        response = await client.put(
            f"/links/{short_code}",
            json={
                "original_url": "https://example.com/updated",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_link_success(self, client: AsyncClient, auth_token: str):
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/original"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert create_response.status_code == 201
        short_code = create_response.json()["short_code"]

        response = await client.put(
            f"/links/{short_code}",
            json={"original_url": "https://example.com/updated"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json()["original_url"] == "https://example.com/updated"

    @pytest.mark.asyncio
    async def test_delete_link_success(self, client: AsyncClient, auth_token: str):
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/original"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert create_response.status_code == 201
        short_code = create_response.json()["short_code"]

        response = await client.delete(
            f"/links/{short_code}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 204

        get_response = await client.get(f"/links/{short_code}/stats")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_link_forbidden(self, client: AsyncClient):
        # Create without auth (anonymous)
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/anonymous"},
        )
        assert create_response.status_code == 201
        short_code = create_response.json()["short_code"]

        # Register hacker user to try to update it
        await client.post(
            "/auth/register",
            json={"username": "hacker", "email": "hacker@example.com", "password": "PassWord123!"},
        )
        login_resp = await client.post(
            "/auth/login",
            data={"username": "hacker", "password": "PassWord123!"},
        )
        hacker_token = login_resp.json()["access_token"]

        response = await client.put(
            f"/links/{short_code}",
            json={"original_url": "https://example.com/hacked"},
            headers={"Authorization": f"Bearer {hacker_token}"},
        )
        assert response.status_code == 403
