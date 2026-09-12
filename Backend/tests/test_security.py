import pytest

from app.core.errors import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_round_trip():
    hashed = hash_password("Passw0rd123")
    assert hashed != "Passw0rd123"
    assert verify_password("Passw0rd123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_password_over_72_bytes_is_rejected_not_truncated():
    """bcrypt truncates silently; two different long passwords must not match."""
    with pytest.raises(ValueError):
        hash_password("a" * 73)


def test_verify_handles_garbage_hash():
    assert verify_password("x", "not-a-hash") is False


def test_access_token_round_trip():
    token, _ = create_access_token(42, "admin")
    claims = decode_token(token, expected_type="access")
    assert claims["sub"] == "42"
    assert claims["role"] == "admin"


def test_token_type_is_enforced():
    """A refresh token must never be usable as an access token."""
    refresh, _, _ = create_refresh_token(42)
    with pytest.raises(AuthenticationError):
        decode_token(refresh, expected_type="access")


def test_tampered_token_is_rejected():
    token, _ = create_access_token(1, "user")
    with pytest.raises(AuthenticationError):
        decode_token(token[:-4] + "aaaa", expected_type="access")


def test_refresh_tokens_are_unique_per_issue():
    _, jti_a, _ = create_refresh_token(1)
    _, jti_b, _ = create_refresh_token(1)
    assert jti_a != jti_b
