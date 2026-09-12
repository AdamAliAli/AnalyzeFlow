"""Dispatch a job according to JOB_RUNNER."""

from __future__ import annotations

from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.job import AnalysisJob

logger = get_logger(__name__)


async def _run_in_own_session(job_id: int) -> None:
    """Background tasks outlive the request, so they need their own session."""
    from app.services.analysis.pipeline import run_analysis

    async with AsyncSessionLocal() as db:
        await run_analysis(db, job_id)


def dispatch(job: AnalysisJob, background: BackgroundTasks) -> None:
    if settings.job_runner == "inline":
        background.add_task(_run_in_own_session, job.analysis_job_id)
    else:
        logger.debug(
            "Job %s left queued for the external worker", job.public_id
        )
