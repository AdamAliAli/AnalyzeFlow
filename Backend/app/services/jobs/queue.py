"""Enqueue and claim analysis jobs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit import AuditSubmission
from app.models.enums import AuditStatus, JobStage, JobStatus
from app.models.job import AnalysisJob


async def enqueue(db: AsyncSession, audit: AuditSubmission) -> AnalysisJob:
    """Create a queued job for an audit. One active job per audit."""
    existing = await db.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.audit_submission_id == audit.audit_submission_id,
            AnalysisJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
        .order_by(AnalysisJob.created_at.desc())
    )
    if existing is not None:
        return existing

    job = AnalysisJob(
        audit_submission_id=audit.audit_submission_id,
        status=JobStatus.QUEUED,
        stage=JobStage.QUEUED,
        progress=0,
        max_attempts=settings.job_max_attempts,
    )
    audit.status = AuditStatus.SUBMITTED
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def claim_next(db: AsyncSession) -> AnalysisJob | None:
    """Atomically take the oldest runnable job.

    FOR UPDATE SKIP LOCKED means two workers never pick the same row, so the
    team can scale to more than one process without any extra infrastructure.
    """
    result = await db.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.status == JobStatus.QUEUED,
            AnalysisJob.attempts < AnalysisJob.max_attempts,
        )
        .order_by(AnalysisJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = result.scalar_one_or_none()
    if job is None:
        await db.rollback()
        return None

    # Mark it RUNNING inside the same transaction that holds the row lock, so
    # no other worker can see it as available. run_analysis() takes over the
    # state machine from here.
    job.status = JobStatus.RUNNING
    await db.commit()
    return job


async def requeue_failed(db: AsyncSession, job: AnalysisJob) -> AnalysisJob:
    """Retry a failed job that still has attempts left."""
    if not job.can_retry:
        return job
    job.status = JobStatus.QUEUED
    job.stage = JobStage.QUEUED
    job.progress = 0
    job.error_code = None
    job.error_message = None
    job.finished_at = None
    await db.commit()
    return job
