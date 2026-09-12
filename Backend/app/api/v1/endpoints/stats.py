"""Numbers for the homepage counters.

The hero currently animates hard-coded targets in index.html. This makes them
real without changing the animation.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.audit import AuditSubmission
from app.models.enums import AuditStatus
from app.models.report import Recommendation


class PublicStats(BaseModel):
    audits_completed: int
    opportunities_found: int
    frameworks: int = 5  # the five-question framework


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=PublicStats)
async def public_stats(db: DbSession) -> PublicStats:
    audits = await db.scalar(
        select(func.count())
        .select_from(AuditSubmission)
        .where(AuditSubmission.status == AuditStatus.ANALYZED)
    )
    recommendations = await db.scalar(
        select(func.count()).select_from(Recommendation)
    )
    return PublicStats(
        audits_completed=audits or 0,
        opportunities_found=recommendations or 0,
    )
