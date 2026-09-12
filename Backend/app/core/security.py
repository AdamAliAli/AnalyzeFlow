"""Password hashing and JWT issue/verify."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AuthenticationError

TokenType = Literal["access", "refresh"]

# bcrypt is used directly rather than through passlib: passlib is unmaintained
# and its bcrypt 4.x backend detection emits a spurious error on every call.
_BCRYPT_ROUNDS = 12
_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    """Hash a password. Raises on >72 bytes rather than silently truncating."""
    encoded = plain.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError("Password is too long (72 bytes maximum).")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_BCRYPT_MAX_BYTES],
                              hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(
    subject: str | int,
    token_type: TokenType,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Returns (encoded_jwt, jti, expires_at)."""
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
    }
    if extra:
        payload.update(extra)
    encoded = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return encoded, jti, expires_at


def create_access_token(user_id: int, role: str) -> tuple[str, datetime]:
    token, _, expires_at = _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        extra={"role": role},
    )
    return token, expires_at


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at). The jti is stored so it can be revoked."""
    return _create_token(
        user_id, "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Token is invalid.") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(
            f"Expected a {expected_type} token, got {payload.get('type')!r}."
        )
    return payload
