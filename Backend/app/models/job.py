"""DB-backed job queue.

Deliberately not Celery/Redis: the team has no budget for extra infrastructure
and every member has to be able to run this locally with one command. The
table gives us durability and retries; `SELECT ... FOR UPDATE SKIP LOCKED`
gives us safe concurrency if more than one worker is ever added.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin
from app.models.enums import JobStage, JobStatus


class AnalysisJob(Base, TimestampMixin):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')",
            name="chk_analysis_jobs_status",
        ),
        Index("idx_analysis_jobs_status_created", "status", "created_at"),
    )

    analysis_job_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=False),
        server_default=func.gen_random_uuid(),
        unique=True,
        nullable=False,
        index=True,
    )

    audit_submission_id: Mapped[int] = mapped_column(
        ForeignKey("audit_submissions.audit_submission_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=JobStatus.QUEUED
    )
    stage: Mapped[str] = mapped_column(
        String(30), nullable=False, default=JobStage.QUEUED
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    audit: Mapped["AuditSubmission"] = relationship(back_populates="jobs")  # noqa: F821

    @property
    def is_terminal(self) -> bool:
        return self.status in (JobStatus.SUCCEEDED, JobStatus.FAILED)

    @property
    def can_retry(self) -> bool:
        return self.status == JobStatus.FAILED and self.attempts < self.max_attempts
