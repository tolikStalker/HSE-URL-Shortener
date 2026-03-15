import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest.mark.unit
class TestUserService:
    @pytest.fixture
    def user_service(self, test_session: AsyncSession):
        return UserService(test_session)

    @pytest.mark.asyncio
    async def test_register_success(self, user_service: UserService):
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
        )

        user = await user_service.register(user_data)

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password != "SecurePassword123!"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, user_service: UserService, test_session: AsyncSession
    ):
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
        )

        await user_service.register(user_data)

        with pytest.raises(HTTPException) as exc_info:
            await user_service.register(
                UserCreate(
                    username="testuser",
                    email="another@example.com",
                    password="AnotherPassword123!",
                )
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_authenticate_success(self, user_service: UserService):
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
        )

        await user_service.register(user_data)

        token = await user_service.authenticate("testuser", "SecurePassword123!")

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, user_service: UserService):
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
        )

        await user_service.register(user_data)

        with pytest.raises(HTTPException) as exc_info:
            await user_service.authenticate("testuser", "WrongPassword")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, user_service: UserService):
        with pytest.raises(HTTPException) as exc_info:
            await user_service.authenticate("nonexistent", "password")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
