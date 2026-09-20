"""Application settings, loaded from environment / .env file."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "AnalyzeFlow API"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://analyzeflow:analyzeflow@localhost:5432/analyzeflow"
    )

    # --- Security ---
    secret_key: str = "change-me-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # --- CORS ---
    # NoDecode stops pydantic-settings from JSON-parsing the env value, so the
    # validator below can accept a plain comma-separated string.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5500"]

    # --- Scraper ---
    scraper_user_agent: str = "AnalyzeFlowBot/1.0"
    scraper_timeout_seconds: float = 15.0
    scraper_max_bytes: int = 3_000_000
    scraper_max_redirects: int = 5
    scraper_allow_private_hosts: bool = False

    # --- AI ---
    ai_provider: str = "mock"
    ai_model: str = ""
    ai_api_key: str = ""
    ai_timeout_seconds: float = 90.0
    ai_max_retries: int = 2

    # --- Platform ---
    # True on serverless hosts (Vercel). Switches the DB to NullPool.
    serverless: bool = False

    # --- Jobs ---
    job_runner: Literal["inline", "worker", "request"] = "inline"
    job_max_attempts: int = 3
    job_poll_interval_seconds: float = 2.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be given as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def sync_database_url(self) -> str:
        """Alembic runs synchronously, so it needs the psycopg/sync URL form."""
        return self.database_url.replace("+asyncpg", "")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
