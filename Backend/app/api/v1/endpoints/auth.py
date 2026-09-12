"""Register, login, refresh, logout, me."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.schemas.common import Message

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_tokens(db: DbSession, user: User) -> TokenPair:
    access_token, expires_at = create_access_token(user.user_id, user.role)
    refresh_token, jti, refresh_expires = create_refresh_token(user.user_id)

    db.add(
        RefreshToken(user_id=user.user_id, jti=jti, expires_at=refresh_expires)
    )
    await db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    email = payload.email.lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ConflictError("An account with that email already exists.")

    user = User(
        full_name=payload.full_name,
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = await _issue_tokens(db, user)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))

    # Same message and roughly the same work either way, so the response does
    # not reveal whether an email is registered.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Email or password is incorrect.")
    if not user.is_active:
        raise AuthenticationError("This account has been disabled.")

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    tokens = await _issue_tokens(db, user)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    jti = claims.get("jti")

    stored = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if stored is None or not stored.is_active:
        raise AuthenticationError("This session has expired. Please sign in again.")

    user = await db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("That account is no longer available.")

    # Rotate: the presented token is burned so a stolen copy is useless.
    stored.revoked_at = datetime.now(UTC)
    await db.commit()

    return await _issue_tokens(db, user)


@router.post("/logout", response_model=Message)
async def logout(payload: RefreshRequest, db: DbSession) -> Message:
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.jti == claims.get("jti"))
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await db.commit()
    return Message(message="Signed out.")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
