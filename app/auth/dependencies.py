import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.dependencies import DbSession
from app.models.user import User

security_scheme = HTTPBearer(auto_error=True)
optional_security_scheme = HTTPBearer(auto_error=False)

AuthCredentials = Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]
OptionalAuthCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(optional_security_scheme)
]


async def _resolve_user(token: str, db: AsyncSession) -> User | None:
    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None

    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: AuthCredentials,
    db: DbSession,
) -> User:
    user = await _resolve_user(credentials.credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


async def get_optional_user(
    credentials: OptionalAuthCredentials,
    db: DbSession,
) -> User | None:
    if credentials is None:
        return None
    return await _resolve_user(credentials.credentials, db)
