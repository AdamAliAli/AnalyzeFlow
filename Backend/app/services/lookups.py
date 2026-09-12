"""Resolve the wizard's display labels to lookup rows.

The front end currently sends labels ("Low Online Visibility"). Slugs are the
stable key. This accepts either, case-insensitively, so a label reword on the
front end can never 500 the backend.
"""

from __future__ import annotations

import re
from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError_
from app.models.lookup import BusinessStage, Challenge, Goal, Industry

T = TypeVar("T", BusinessStage, Challenge, Goal, Industry)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


async def resolve(
    db: AsyncSession, model: type[T], value: str, field_label: str
) -> T:
    candidate = (value or "").strip()
    if not candidate:
        raise ValidationError_(f"{field_label} is required.")

    row = await db.scalar(
        select(model).where(
            (func.lower(model.slug) == candidate.lower())
            | (func.lower(model.name) == candidate.lower())
            | (model.slug == slugify(candidate))
        )
    )
    if row is None:
        options = await db.scalars(select(model.name).where(model.is_active.is_(True)))
        raise ValidationError_(
            f"{field_label} {candidate!r} is not recognised.",
            {"allowed": sorted(options)},
        )
    return row


async def resolve_many(
    db: AsyncSession, model: type[T], values: list[str], field_label: str
) -> list[T]:
    return [await resolve(db, model, value, field_label) for value in values]


async def resolve_optional(
    db: AsyncSession, model: type[T], value: str | None
) -> T | None:
    """For industry, where an unrecognised value is stored as free text."""
    if not value or not value.strip():
        return None
    candidate = value.strip()
    return await db.scalar(
        select(model).where(
            (func.lower(model.slug) == candidate.lower())
            | (func.lower(model.name) == candidate.lower())
            | (model.slug == slugify(candidate))
        )
    )
