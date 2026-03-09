from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
RequestForm = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: DbSession):
    service = UserService(db)
    return await service.register(data)


@router.post("/login", response_model=Token)
async def login(
    form_data: RequestForm,
    db: DbSession,
):
    service = UserService(db)
    token = await service.authenticate(form_data.username, form_data.password)
    return Token(access_token=token)
