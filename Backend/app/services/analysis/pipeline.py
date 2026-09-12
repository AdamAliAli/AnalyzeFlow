"""Orchestrates one full analysis run.

    fetch site -> extract content -> compute signals -> run AI -> persist report

Each stage updates the job row so the front end's progress screen has
something real to show. The whole thing is idempotent per audit: re-running
replaces the previous snapshot and report.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.audit import AuditSubmission
from app.models.enums import AuditStatus, JobStage, JobStatus, SnapshotStatus
from app.models.job import AnalysisJob
from app.models.report import Recommendation, Report, ReportFinding
from app.models.snapshot import SiteSnapshot
from app.services.ai.contract import (
    AnalysisInput,
    AnalysisOutput,
    AnalyzerError,
    BusinessContext,
    SiteEvidence,
)
from app.services.ai.mock_provider import MockAnalyzerProvider
from app.services.ai.registry import get_provider
from app.services.scraper import extractor
from app.services.scraper.fetcher import FetchError, fetch_page
from app.services.scraper.signals import compute

logger = get_logger(__name__)


async def _set_stage(
    db: AsyncSession, job: AnalysisJob, stage: JobStage, progress: int
) -> None:
    job.stage = stage
    job.progress = progress
    await db.commit()


async def run_analysis(db: AsyncSession, job_id: int) -> None:
    """Execute one job. Never raises - failures are recorded on the job row."""
    job = await db.get(AnalysisJob, job_id)
    if job is None:
        logger.error("Job %s disappeared before it could run", job_id)
        return
    # RUNNING is accepted because the worker claims a job by setting it there
    # under a row lock before handing it over.
    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.FAILED):
        logger.info("Job %s is %s, skipping", job_id, job.status)
        return

    audit = await db.get(AuditSubmission, job.audit_submission_id)
    if audit is None:
        await _fail(db, job, "audit_missing", "The audit no longer exists.")
        return

    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.started_at = datetime.now(UTC)
    audit.status = AuditStatus.ANALYZING
    await db.commit()

    try:
        # ---- 1. Fetch -----------------------------------------------------
        await _set_stage(db, job, JobStage.FETCHING_SITE, 10)
        try:
            fetched = await fetch_page(audit.target_url)
        except FetchError as exc:
            await _save_failed_snapshot(db, audit, exc)
            await _fail(db, job, exc.code, exc.message, retryable=False)
            return

        # ---- 2. Extract + signals ----------------------------------------
        await _set_stage(db, job, JobStage.EXTRACTING_SIGNALS, 35)
        content = extractor.extract(fetched.html, fetched.final_url)
        site_signals = compute(content, fetched)

        snapshot = await _upsert_snapshot(db, audit, fetched, content, site_signals)

        # ---- 3. Analyse ---------------------------------------------------
        await _set_stage(db, job, JobStage.RUNNING_ANALYSIS, 55)
        payload = _build_input(audit, content, site_signals, fetched)
        analysis, duration_ms = await _analyze_with_fallback(payload)

        # ---- 4. Persist ---------------------------------------------------
        await _set_stage(db, job, JobStage.SAVING_REPORT, 85)
        await _save_report(db, audit, analysis, duration_ms)

        audit.status = AuditStatus.ANALYZED
        job.status = JobStatus.SUCCEEDED
        job.stage = JobStage.DONE
        job.progress = 100
        job.finished_at = datetime.now(UTC)
        job.error_code = None
        job.error_message = None
        await db.commit()

        logger.info(
            "Analysis complete for audit %s (%s, %sms)",
            audit.public_id,
            analysis.provider,
            duration_ms,
        )
        _ = snapshot

    except Exception as exc:
        logger.exception("Analysis job %s failed unexpectedly", job_id)
        await db.rollback()
        await _fail(db, job, "internal_error", str(exc)[:500], retryable=False)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------


def _build_input(
    audit: AuditSubmission,
    content: extractor.PageContent,
    site_signals,
    fetched,
) -> AnalysisInput:
    profile = audit.business_profile
    return AnalysisInput(
        business=BusinessContext(
            business_name=profile.business_name,
            website_url=audit.target_url,
            industry=profile.industry_label,
            goal=audit.goal.name,
            challenges=[c.name for c in audit.challenges],
            business_stage=audit.business_stage.name,
            business_description=profile.business_description,
        ),
        site=SiteEvidence(
            final_url=fetched.final_url,
            http_status=fetched.http_status,
            fetch_duration_ms=fetched.duration_ms,
            page_title=content.title,
            meta_description=content.meta_description,
            headings_h1=content.h1,
            headings_h2=content.h2,
            visible_text=content.text_content,
            cta_labels=content.buttons,
            form_count=len(content.forms),
            image_count=len(content.images),
            images_missing_alt=sum(1 for i in content.images if not i.has_alt),
            social_links=content.social_links,
            detected_platform=content.platform_detected,
            detected_analytics=content.analytics_detected,
            rule_signals=site_signals.signals,
            rule_scores={
                "visual": site_signals.visual_score,
                "technical": site_signals.technical_score,
                "business": site_signals.business_score,
                "overall": site_signals.overall_score,
            },
        ),
    )


async def _analyze_with_fallback(
    payload: AnalysisInput,
) -> tuple[AnalysisOutput, int]:
    """Try the configured provider, retry, then degrade to the rule engine."""
    provider = get_provider()
    started = time.perf_counter()

    attempts = max(1, settings.ai_max_retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            result = await provider.analyze(payload)
            return result, int((time.perf_counter() - started) * 1000)
        except AnalyzerError as exc:
            logger.warning(
                "AI provider %r failed (attempt %s/%s): %s",
                getattr(provider, "name", "?"),
                attempt,
                attempts,
                exc.message,
            )
            if not exc.retryable or attempt == attempts:
                break
        except Exception:
            logger.exception("AI provider raised an unexpected error")
            break

    if isinstance(provider, MockAnalyzerProvider):
        raise AnalyzerError("The rule-based analyzer failed.", retryable=False)

    logger.warning("Falling back to the rule-based analyzer for this report.")
    fallback = await MockAnalyzerProvider().analyze(payload)
    fallback.provider = "mock-fallback"
    return fallback, int((time.perf_counter() - started) * 1000)


async def _upsert_snapshot(
    db: AsyncSession, audit: AuditSubmission, fetched, content, site_signals
) -> SiteSnapshot:
    await db.execute(
        delete(SiteSnapshot).where(
            SiteSnapshot.audit_submission_id == audit.audit_submission_id
        )
    )
    snapshot = SiteSnapshot(
        audit_submission_id=audit.audit_submission_id,
        requested_url=fetched.requested_url,
        final_url=fetched.final_url,
        status=SnapshotStatus.OK,
        http_status=fetched.http_status,
        fetch_duration_ms=fetched.duration_ms,
        content_bytes=fetched.content_bytes,
        extracted=content.to_dict(),
        signals=site_signals.to_dict(),
        text_content=content.text_content,
    )
    db.add(snapshot)
    await db.commit()
    return snapshot


async def _save_failed_snapshot(
    db: AsyncSession, audit: AuditSubmission, exc: FetchError
) -> None:
    await db.execute(
        delete(SiteSnapshot).where(
            SiteSnapshot.audit_submission_id == audit.audit_submission_id
        )
    )
    status = (
        SnapshotStatus.BLOCKED if exc.code == "blocked" else SnapshotStatus.UNREACHABLE
    )
    db.add(
        SiteSnapshot(
            audit_submission_id=audit.audit_submission_id,
            requested_url=audit.target_url,
            status=status,
            error_message=exc.message,
            extracted={},
            signals={},
        )
    )
    audit.status = AuditStatus.FAILED
    await db.commit()


async def _save_report(
    db: AsyncSession,
    audit: AuditSubmission,
    analysis: AnalysisOutput,
    duration_ms: int,
) -> Report:
    existing = await db.scalar(
        select(Report).where(Report.audit_submission_id == audit.audit_submission_id)
    )
    if existing is not None:
        await db.delete(existing)
        await db.flush()

    report = Report(
        audit_submission_id=audit.audit_submission_id,
        overall_score=analysis.scores.overall,
        visual_score=analysis.scores.visual,
        technical_score=analysis.scores.technical,
        business_score=analysis.scores.business,
        executive_summary=analysis.executive_summary,
        provider=analysis.provider,
        model=analysis.model,
        analysis_duration_ms=duration_ms,
        raw_output=analysis.model_dump(mode="json"),
    )
    db.add(report)
    await db.flush()

    for order, finding in enumerate(analysis.findings):
        db.add(
            ReportFinding(
                report_id=report.report_id,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                description=finding.description,
                evidence=finding.evidence,
                display_order=order,
            )
        )

    for rec in analysis.recommendations:
        db.add(
            Recommendation(
                report_id=report.report_id,
                title=rec.title,
                description=rec.description,
                category=rec.category,
                priority=rec.priority,
                effort=rec.effort,
                impact=rec.impact,
                first_step=rec.first_step,
            )
        )

    # Write the AI-inferred framework answers back onto the audit.
    framework = analysis.framework
    audit.client_description = framework.client_description
    audit.user_description = framework.user_description
    audit.problem_description = framework.problem_description
    audit.value_creation_description = framework.value_creation_description
    audit.revenue_model_description = framework.revenue_model_description

    await db.commit()
    return report


async def _fail(
    db: AsyncSession,
    job: AnalysisJob,
    code: str,
    message: str,
    retryable: bool = True,
) -> None:
    job.status = JobStatus.FAILED
    job.error_code = code
    job.error_message = message
    job.finished_at = datetime.now(UTC)
    if not retryable:
        job.attempts = job.max_attempts  # stop the worker retrying a hopeless job

    audit = await db.get(AuditSubmission, job.audit_submission_id)
    if audit is not None:
        audit.status = AuditStatus.FAILED
    await db.commit()
