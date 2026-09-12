"""CRUD for the signed-in user's business profiles."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.models.business import BusinessProfile
from app.models.lookup import Industry
from app.schemas.business import (
    BusinessProfileCreate,
    BusinessProfileOut,
    BusinessProfileUpdate,
)
from app.schemas.common import Message
from app.services import lookups

router = APIRouter(prefix="/businesses", tags=["businesses"])


async def _owned(db: DbSession, profile_id: int, user) -> BusinessProfile:
    profile = await db.get(BusinessProfile, profile_id)
    if profile is None or profile.user_id != user.user_id:
        raise NotFoundError("That business profile does not exist.")
    return profile


@router.get("", response_model=list[BusinessProfileOut])
async def list_businesses(
    db: DbSession, user: CurrentUser
) -> list[BusinessProfileOut]:
    rows = await db.scalars(
        select(BusinessProfile)
        .where(BusinessProfile.user_id == user.user_id)
        .order_by(BusinessProfile.created_at.desc())
    )
    return [BusinessProfileOut.from_model(p) for p in rows]


@router.post(
    "", response_model=BusinessProfileOut, status_code=status.HTTP_201_CREATED
)
async def create_business(
    payload: BusinessProfileCreate, db: DbSession, user: CurrentUser
) -> BusinessProfileOut:
    industry = await lookups.resolve_optional(db, Industry, payload.industry)
    profile = BusinessProfile(
        user_id=user.user_id,
        business_name=payload.business_name,
        website_url=payload.website_url,
        industry_id=industry.industry_id if industry else None,
        industry_other=None if industry else payload.industry,
        business_description=payload.business_description,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return BusinessProfileOut.from_model(profile)


@router.get("/{profile_id}", response_model=BusinessProfileOut)
async def get_business(
    profile_id: int, db: DbSession, user: CurrentUser
) -> BusinessProfileOut:
    return BusinessProfileOut.from_model(await _owned(db, profile_id, user))


@router.patch("/{profile_id}", response_model=BusinessProfileOut)
async def update_business(
    profile_id: int,
    payload: BusinessProfileUpdate,
    db: DbSession,
    user: CurrentUser,
) -> BusinessProfileOut:
    profile = await _owned(db, profile_id, user)
    data = payload.model_dump(exclude_unset=True)

    if "industry" in data:
        industry = await lookups.resolve_optional(db, Industry, data.pop("industry"))
        profile.industry_id = industry.industry_id if industry else None
        profile.industry_other = None if industry else payload.industry

    for key, value in data.items():
        setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return BusinessProfileOut.from_model(profile)


@router.delete("/{profile_id}", response_model=Message)
async def delete_business(
    profile_id: int, db: DbSession, user: CurrentUser
) -> Message:
    profile = await _owned(db, profile_id, user)
    await db.delete(profile)
    await db.commit()
    return Message(message="Business profile deleted.")
