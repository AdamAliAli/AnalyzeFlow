"""The wizard's fixed choices, served from the database.

Right now the front end hard-codes these in index.html. Once it calls this
endpoint instead, an admin can add an industry without a front-end deploy.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.lookup import BusinessStage, Challenge, Goal, Industry
from app.schemas.lookup import LookupBundle, LookupItem

router = APIRouter(prefix="/lookups", tags=["lookups"])

_PK = {
    Industry: "industry_id",
    Goal: "goal_id",
    Challenge: "challenge_id",
    BusinessStage: "business_stage_id",
}


async def _items(db: DbSession, model: type) -> list[LookupItem]:
    rows = await db.scalars(
        select(model)
        .where(model.is_active.is_(True))
        .order_by(model.sort_order, model.name)
    )
    return [
        LookupItem(
            id=getattr(row, _PK[model]),
            name=row.name,
            slug=row.slug,
            description=row.description,
        )
        for row in rows
    ]


@router.get("", response_model=LookupBundle)
async def all_lookups(db: DbSession) -> LookupBundle:
    """One call returns everything the wizard needs to render."""
    return LookupBundle(
        industries=await _items(db, Industry),
        goals=await _items(db, Goal),
        challenges=await _items(db, Challenge),
        business_stages=await _items(db, BusinessStage),
    )


@router.get("/industries", response_model=list[LookupItem])
async def industries(db: DbSession) -> list[LookupItem]:
    return await _items(db, Industry)


@router.get("/goals", response_model=list[LookupItem])
async def goals(db: DbSession) -> list[LookupItem]:
    return await _items(db, Goal)


@router.get("/challenges", response_model=list[LookupItem])
async def challenges(db: DbSession) -> list[LookupItem]:
    return await _items(db, Challenge)


@router.get("/business-stages", response_model=list[LookupItem])
async def business_stages(db: DbSession) -> list[LookupItem]:
    return await _items(db, BusinessStage)
