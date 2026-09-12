from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.models.enums import AuditStatus


class AuditSubmission(Base, TimestampMixin):
    __tablename__ = "audit_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','submitted','analyzing','analyzed','failed')",
            name="chk_audit_submissions_status",
        ),
        Index("idx_audit_submissions_business_profile_id", "business_profile_id"),
        Index("idx_audit_submissions_status", "status"),
    )

    audit_submission_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Public, unguessable handle. The front end polls and shares by this, never
    # by the integer id.
    public_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=False),
        server_default=func.gen_random_uuid(),
        unique=True,
        nullable=False,
        index=True,
    )

    business_profile_id: Mapped[int] = mapped_column(
        ForeignKey("business_profiles.business_profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    business_stage_id: Mapped[int] = mapped_column(
        ForeignKey("business_stages.business_stage_id", ondelete="RESTRICT"),
        nullable=False,
    )
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.goal_id", ondelete="RESTRICT"), nullable=False
    )

    # The URL actually analysed, frozen at submission time. The business
    # profile's URL can change later; a report must stay reproducible.
    target_url: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AuditStatus.SUBMITTED
    )

    # --- The five framework answers ---------------------------------------
    # In the team's original schema these were user inputs, but the wizard
    # never collects them. Under the current product direction they are
    # INFERRED BY THE AI from the fetched website, and written back here.
    client_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_creation_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_model_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    business_profile: Mapped["BusinessProfile"] = relationship(  # noqa: F821
        back_populates="audits", lazy="joined"
    )
    business_stage: Mapped["BusinessStage"] = relationship(lazy="joined")  # noqa: F821
    goal: Mapped["Goal"] = relationship(lazy="joined")  # noqa: F821
    challenges: Mapped[list["Challenge"]] = relationship(  # noqa: F821
        secondary="audit_challenges", lazy="selectin"
    )
    snapshot: Mapped["SiteSnapshot | None"] = relationship(  # noqa: F821
        back_populates="audit", cascade="all, delete-orphan", uselist=False
    )
    report: Mapped["Report | None"] = relationship(  # noqa: F821
        back_populates="audit", cascade="all, delete-orphan", uselist=False
    )
    jobs: Mapped[list["AnalysisJob"]] = relationship(  # noqa: F821
        back_populates="audit", cascade="all, delete-orphan"
    )


class AuditChallenge(Base, CreatedAtMixin):
    """Many-to-many join: one audit selects one or more challenges."""

    __tablename__ = "audit_challenges"

    audit_submission_id: Mapped[int] = mapped_column(
        ForeignKey("audit_submissions.audit_submission_id", ondelete="CASCADE"),
        primary_key=True,
    )
    challenge_id: Mapped[int] = mapped_column(
        ForeignKey("challenges.challenge_id", ondelete="RESTRICT"), primary_key=True
    )
