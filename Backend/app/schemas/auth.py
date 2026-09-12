from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def _strength(cls, value: str) -> str:
        if value.isdigit() or value.isalpha():
            raise ValueError(
                "Password must contain both letters and numbers."
            )
        # bcrypt truncates beyond 72 bytes; reject instead of silently cutting.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long (72 bytes maximum).")
        return value

    @field_validator("full_name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class UserOut(ORMModel):
    user_id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
    tokens: TokenPair
