import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_json_payload(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            content=b"invalid json",
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_field(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_url_format(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "not-a-valid-url",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_custom_alias_invalid_format(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com",
                "custom_alias": "inv@lid",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, client: AsyncClient):
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
