"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, PermissionError_
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Sign in to continue.")

    payload = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("Token is malformed.") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise AuthenticationError("That account no longer exists.")
    if not user.is_active:
        raise PermissionError_("This account has been disabled.")
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_admin:
        raise PermissionError_("Administrator access is required.")
    return user


async def get_optional_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User | None:
    """For endpoints that behave differently when signed in but don't require it."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await get_current_user(db, credentials)
    except (AuthenticationError, PermissionError_):
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
OptionalUser = Annotated["User | None", Depends(get_optional_user)]
