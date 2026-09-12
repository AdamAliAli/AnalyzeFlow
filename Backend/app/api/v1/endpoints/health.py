from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings
from app.services.ai.registry import available_providers


class Health(BaseModel):
    status: str
    environment: str
    database: str
    ai_provider: str
    ai_providers_available: list[str]
    job_runner: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
async def health(db: DbSession) -> Health:
    try:
        await db.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:
        database = f"error: {type(exc).__name__}"

    return Health(
        status="ok" if database == "ok" else "degraded",
        environment=settings.environment,
        database=database,
        ai_provider=settings.ai_provider,
        ai_providers_available=available_providers(),
        job_runner=settings.job_runner,
    )
