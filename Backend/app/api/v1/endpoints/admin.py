"""Admin-only content management.

Backs the `is_active` / `is_published` flags that already exist in the team's
schema but had no way to be toggled.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentAdmin, DbSession
from app.core.errors import ConflictError, NotFoundError
from app.models.case_study import CaseStudy
from app.models.lookup import BusinessStage, Challenge, Goal, Industry
from app.schemas.common import Message
from app.schemas.lookup import LookupItem
from app.schemas.report import CaseStudyOut
from app.services.lookups import slugify

router = APIRouter(prefix="/admin", tags=["admin"])

_MODELS = {
    "industries": (Industry, "industry_id"),
    "goals": (Goal, "goal_id"),
    "challenges": (Challenge, "challenge_id"),
    "business-stages": (BusinessStage, "business_stage_id"),
}


class LookupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    slug: str | None = None
    description: str | None = None
    sort_order: int = 0


class LookupPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CaseStudyIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = None
    summary: str
    content: str
    industry_label: str | None = None
    client_type: str | None = None
    user_type: str | None = None
    problem: str | None = None
    value_proposition: str | None = None
    revenue_model: str | None = None
    key_insight: str | None = None
    is_published: bool = False


def _model_for(kind: str):
    if kind not in _MODELS:
        raise NotFoundError(
            f"Unknown lookup {kind!r}.", {"allowed": sorted(_MODELS)}
        )
    return _MODELS[kind]


@router.post(
    "/lookups/{kind}", response_model=LookupItem, status_code=status.HTTP_201_CREATED
)
async def create_lookup(
    kind: str, payload: LookupCreate, db: DbSession, _: CurrentAdmin
) -> LookupItem:
    model, pk = _model_for(kind)
    slug = payload.slug or slugify(payload.name)

    if await db.scalar(select(model).where(model.slug == slug)):
        raise ConflictError(f"A {kind[:-1]} with slug {slug!r} already exists.")

    row = model(
        name=payload.name,
        slug=slug,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return LookupItem(
        id=getattr(row, pk), name=row.name, slug=row.slug, description=row.description
    )


@router.patch("/lookups/{kind}/{item_id}", response_model=LookupItem)
async def update_lookup(
    kind: str, item_id: int, payload: LookupPatch, db: DbSession, _: CurrentAdmin
) -> LookupItem:
    model, pk = _model_for(kind)
    row = await db.get(model, item_id)
    if row is None:
        raise NotFoundError("That item does not exist.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return LookupItem(
        id=getattr(row, pk), name=row.name, slug=row.slug, description=row.description
    )


@router.get("/case-studies", response_model=list[CaseStudyOut])
async def list_all_case_studies(
    db: DbSession, _: CurrentAdmin
) -> list[CaseStudyOut]:
    rows = await db.scalars(select(CaseStudy).order_by(CaseStudy.created_at.desc()))
    return [CaseStudyOut.model_validate(row) for row in rows]


@router.post(
    "/case-studies", response_model=CaseStudyOut, status_code=status.HTTP_201_CREATED
)
async def create_case_study(
    payload: CaseStudyIn, db: DbSession, _: CurrentAdmin
) -> CaseStudyOut:
    slug = payload.slug or slugify(payload.title)
    if await db.scalar(select(CaseStudy).where(CaseStudy.slug == slug)):
        raise ConflictError(f"A case study with slug {slug!r} already exists.")

    row = CaseStudy(**{**payload.model_dump(), "slug": slug})
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return CaseStudyOut.model_validate(row)


@router.patch("/case-studies/{case_study_id}", response_model=CaseStudyOut)
async def update_case_study(
    case_study_id: int, payload: CaseStudyIn, db: DbSession, _: CurrentAdmin
) -> CaseStudyOut:
    row = await db.get(CaseStudy, case_study_id)
    if row is None:
        raise NotFoundError("That case study does not exist.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "slug" and not value:
            continue
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return CaseStudyOut.model_validate(row)


@router.delete("/case-studies/{case_study_id}", response_model=Message)
async def delete_case_study(
    case_study_id: int, db: DbSession, _: CurrentAdmin
) -> Message:
    row = await db.get(CaseStudy, case_study_id)
    if row is None:
        raise NotFoundError("That case study does not exist.")
    await db.delete(row)
    await db.commit()
    return Message(message="Case study deleted.")
