"""Public marketing content for the homepage and case-study page."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.errors import NotFoundError
from app.models.case_study import CaseStudy
from app.schemas.report import CaseStudyOut, CaseStudySummaryOut

router = APIRouter(prefix="/case-studies", tags=["case-studies"])


@router.get("", response_model=list[CaseStudySummaryOut])
async def list_case_studies(db: DbSession) -> list[CaseStudySummaryOut]:
    rows = await db.scalars(
        select(CaseStudy)
        .where(CaseStudy.is_published.is_(True))
        .order_by(CaseStudy.created_at.desc())
    )
    return [CaseStudySummaryOut.model_validate(row) for row in rows]


@router.get("/{slug}", response_model=CaseStudyOut)
async def get_case_study(slug: str, db: DbSession) -> CaseStudyOut:
    row = await db.scalar(
        select(CaseStudy).where(
            CaseStudy.slug == slug, CaseStudy.is_published.is_(True)
        )
    )
    if row is None:
        raise NotFoundError("That case study does not exist.")
    return CaseStudyOut.model_validate(row)
