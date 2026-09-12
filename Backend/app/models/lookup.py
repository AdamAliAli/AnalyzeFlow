"""Reference tables the wizard's fixed choices resolve against.

The front end currently sends display labels ("Low Online Visibility").
These tables hold both `name` (label) and `slug` (stable key) so the API can
accept either and never break when a label is reworded.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin


class _LookupMixin(CreatedAtMixin):
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)


class BusinessStage(Base, _LookupMixin):
    __tablename__ = "business_stages"
    business_stage_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class Challenge(Base, _LookupMixin):
    __tablename__ = "challenges"
    challenge_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class Goal(Base, _LookupMixin):
    """Wizard step 2. Was a free-text column in the team's original schema."""

    __tablename__ = "goals"
    goal_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class Industry(Base, _LookupMixin):
    """Wizard step 1 dropdown. Was a free-text column originally."""

    __tablename__ = "industries"
    industry_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
