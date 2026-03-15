from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient):
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }

        await client.post("/auth/register", json=user_data)

        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "another@example.com",
                "password": "AnotherPassword123!",
            },
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
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

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
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
                "password": "WrongPassword",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/auth/login",
            data={
                "username": "nonexistent",
                "password": "password",
            },
        )

        assert response.status_code == 401


@pytest.mark.integration
class TestInputValidation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("username", ["ab", "a"])
    async def test_register_username_too_short(self, client: AsyncClient, username: str):
        response = await client.post(
            "/auth/register",
            json={"username": username, "email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_username_too_long(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "username": "a" * 51,
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_username_boundary_min(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={"username": "abc", "email": "abc@example.com", "password": "password123"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_register_username_missing(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize("password", ["", "12345"])
    async def test_register_password_too_short(self, client: AsyncClient, password: str):
        response = await client.post(
            "/auth/register",
            json={"username": "testuser", "email": "test@example.com", "password": password},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_too_long(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "x" * 129,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_boundary_min(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={"username": "testuser2", "email": "test2@example.com", "password": "123456"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "email",
        [
            "not-an-email",
            "missing@",
            "@no-local.com",
            "spaces in@email.com",
            "double@@email.com",
        ],
    )
    async def test_register_invalid_email_formats(self, client: AsyncClient, email: str):
        response = await client.post(
            "/auth/register",
            json={"username": "testuser", "email": email, "password": "password123"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_numeric_username(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={"username": 12345, "email": "test@example.com", "password": "password123"},
        )
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_register_null_fields(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={"username": None, "email": None, "password": None},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_empty_body(self, client: AsyncClient):
        response = await client.post("/auth/register", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_with_cyrillic(self, client: AsyncClient):
        """Russian chars are valid unicode strings — should pass if length is OK"""
        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser_ru",
                "email": "russian@example.com",
                "password": "Пароль123",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_register_password_only_cyrillic_too_short(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={"username": "testuser_ru2", "email": "r2@example.com", "password": "Пр"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_whitespace_only(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={"username": "testuser_ws", "email": "ws@example.com", "password": "      "},
        )
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_register_password_with_special_chars(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "username": "special_user",
                "email": "special@example.com",
                "password": "P@$$w0rd!",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_register_email_with_plus_alias(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "username": "plus_user",
                "email": "user+tag@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_register_email_subdomains(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "username": "subdomain_user",
                "email": "user@mail.subdomain.example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201


@pytest.mark.integration
class TestLinksValidation:
    @pytest.mark.asyncio
    async def test_shorten_empty_url(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={"original_url": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_missing_url(self, client: AsyncClient):
        response = await client.post("/links/shorten", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_null_url(self, client: AsyncClient):
        response = await client.post("/links/shorten", json={"original_url": None})
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "not-a-url",
            "ftp://example.com",
            "//example.com/no-scheme",
            "example.com",
            "http://",
        ],
    )
    async def test_shorten_invalid_url_format(self, client: AsyncClient, url: str):
        response = await client.post("/links/shorten", json={"original_url": url})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_custom_alias_too_short(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com", "custom_alias": "ab"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_custom_alias_too_long(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com", "custom_alias": "a" * 21},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "alias",
        [
            "my alias",
            "my/alias",
            "my.alias",
            "мой-alias",
            "<script>",
            "alias!",
        ],
    )
    async def test_shorten_custom_alias_invalid_chars(self, client: AsyncClient, alias: str):
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com", "custom_alias": alias},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_custom_alias_valid_boundary_min(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/alias-min", "custom_alias": "abc"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_shorten_custom_alias_valid_boundary_max(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/alias-max",
                "custom_alias": "a" * 20,
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_shorten_past_expires_at(self, client: AsyncClient):

        past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/expire", "expires_at": past},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_url_very_long(self, client: AsyncClient):
        long_url = "https://example.com/" + "a" * 2000
        response = await client.post("/links/shorten", json={"original_url": long_url})
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_shorten_empty_body(self, client: AsyncClient):
        response = await client.post(
            "/links/shorten", content=b"", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
