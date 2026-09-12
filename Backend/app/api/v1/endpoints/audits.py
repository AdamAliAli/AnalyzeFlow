"""Submit an audit, poll its job, list past audits."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.errors import NotFoundError, PermissionError_, ValidationError_
from app.models.audit import AuditChallenge, AuditSubmission
from app.models.business import BusinessProfile
from app.models.enums import AuditStatus, JobStatus
from app.models.job import AnalysisJob
from app.models.lookup import BusinessStage, Challenge, Goal, Industry
from app.models.report import Report
from app.schemas.audit import AuditCreate, AuditCreated, AuditOut, JobOut
from app.schemas.common import Page
from app.services import lookups
from app.services.jobs import queue, runner
from app.services.scraper.fetcher import FetchError, normalize_url

router = APIRouter(prefix="/audits", tags=["audits"])


async def _load_audit(db: DbSession, audit_id: str, user) -> AuditSubmission:
    audit = await db.scalar(
        select(AuditSubmission).where(AuditSubmission.public_id == audit_id)
    )
    if audit is None:
        raise NotFoundError("That audit does not exist.")
    if audit.business_profile.user_id != user.user_id and not user.is_admin:
        raise PermissionError_("You do not have access to that audit.")
    return audit


@router.post("", response_model=AuditCreated, status_code=status.HTTP_201_CREATED)
async def create_audit(
    payload: AuditCreate,
    db: DbSession,
    user: CurrentUser,
    background: BackgroundTasks,
) -> AuditCreated:
    """Submit the wizard. Returns immediately; the report is built in the background.

    The front end must then poll `poll_url` until `job.status` is
    `succeeded` or `failed`.
    """
    try:
        target_url = normalize_url(payload.website_url)
    except FetchError as exc:
        raise ValidationError_(exc.message, {"field": "website_url"}) from exc

    goal = await lookups.resolve(db, Goal, payload.goal, "Goal")
    stage = await lookups.resolve(
        db, BusinessStage, payload.business_stage, "Business stage"
    )
    challenge_rows = await lookups.resolve_many(
        db, Challenge, payload.challenges, "Challenge"
    )
    industry = await lookups.resolve_optional(db, Industry, payload.industry)

    # --- business profile ---
    if payload.business_profile_id is not None:
        profile = await db.get(BusinessProfile, payload.business_profile_id)
        if profile is None or profile.user_id != user.user_id:
            raise NotFoundError("That business profile does not exist.")
        profile.business_name = payload.business_name
        profile.website_url = target_url
        profile.industry_id = industry.industry_id if industry else None
        profile.industry_other = None if industry else payload.industry
    else:
        profile = BusinessProfile(
            user_id=user.user_id,
            business_name=payload.business_name,
            website_url=target_url,
            industry_id=industry.industry_id if industry else None,
            industry_other=None if industry else payload.industry,
            business_description=payload.business_description,
        )
        db.add(profile)
        await db.flush()

    audit = AuditSubmission(
        business_profile_id=profile.business_profile_id,
        business_stage_id=stage.business_stage_id,
        goal_id=goal.goal_id,
        target_url=target_url,
        status=AuditStatus.SUBMITTED,
    )
    db.add(audit)
    await db.flush()

    for challenge in challenge_rows:
        db.add(
            AuditChallenge(
                audit_submission_id=audit.audit_submission_id,
                challenge_id=challenge.challenge_id,
            )
        )
    await db.commit()
    await db.refresh(audit)

    job = await queue.enqueue(db, audit)
    runner.dispatch(job, background)

    return AuditCreated(
        audit=AuditOut.from_model(audit),
        job=JobOut.from_model(job),
        poll_url=f"{settings.api_v1_prefix}/audits/{audit.public_id}/job",
    )


@router.get("/{audit_id}/job", response_model=JobOut)
async def get_job(audit_id: str, db: DbSession, user: CurrentUser) -> JobOut:
    """Poll this every ~2 seconds until status is 'succeeded' or 'failed'."""
    audit = await _load_audit(db, audit_id, user)
    job = await db.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.audit_submission_id == audit.audit_submission_id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    if job is None:
        raise NotFoundError("No analysis has been started for that audit.")
    return JobOut.from_model(job)


@router.post("/{audit_id}/retry", response_model=JobOut)
async def retry_audit(
    audit_id: str, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> JobOut:
    """Re-run a failed analysis, e.g. after the site comes back online."""
    audit = await _load_audit(db, audit_id, user)
    job = await db.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.audit_submission_id == audit.audit_submission_id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    if job is not None and job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        return JobOut.from_model(job)

    if job is not None and job.can_retry:
        job = await queue.requeue_failed(db, job)
    else:
        job = AnalysisJob(audit_submission_id=audit.audit_submission_id)
        db.add(job)
        await db.commit()
        await db.refresh(job)

    runner.dispatch(job, background)
    return JobOut.from_model(job)


@router.get("", response_model=Page[AuditOut])
async def list_audits(
    db: DbSession, user: CurrentUser, page: int = 1, page_size: int = 20
) -> Page[AuditOut]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    base = (
        select(AuditSubmission)
        .join(BusinessProfile)
        .where(BusinessProfile.user_id == user.user_id)
    )
    total = await db.scalar(
        select(func.count())
        .select_from(AuditSubmission)
        .join(BusinessProfile)
        .where(BusinessProfile.user_id == user.user_id)
    )
    rows = await db.scalars(
        base.order_by(AuditSubmission.submitted_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    audits = list(rows)

    reported = set()
    if audits:
        ids = [a.audit_submission_id for a in audits]
        reported = set(
            await db.scalars(
                select(Report.audit_submission_id).where(
                    Report.audit_submission_id.in_(ids)
                )
            )
        )

    return Page(
        items=[
            AuditOut.from_model(a, has_report=a.audit_submission_id in reported)
            for a in audits
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{audit_id}", response_model=AuditOut)
async def get_audit(audit_id: str, db: DbSession, user: CurrentUser) -> AuditOut:
    audit = await _load_audit(db, audit_id, user)
    has_report = (
        await db.scalar(
            select(func.count())
            .select_from(Report)
            .where(Report.audit_submission_id == audit.audit_submission_id)
        )
    ) > 0
    return AuditOut.from_model(audit, has_report=has_report)
