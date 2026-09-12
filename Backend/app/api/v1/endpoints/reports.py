"""Fetch the finished report."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError, PermissionError_
from app.models.audit import AuditSubmission
from app.models.report import Report
from app.models.snapshot import SiteSnapshot
from app.schemas.report import (
    FindingOut,
    FrameworkOut,
    RecommendationOut,
    ReportOut,
    ScoresOut,
    SignalOut,
    SiteInfoOut,
)

router = APIRouter(tags=["reports"])


@router.get("/audits/{audit_id}/report", response_model=ReportOut)
async def get_report(audit_id: str, db: DbSession, user: CurrentUser) -> ReportOut:
    audit = await db.scalar(
        select(AuditSubmission).where(AuditSubmission.public_id == audit_id)
    )
    if audit is None:
        raise NotFoundError("That audit does not exist.")
    if audit.business_profile.user_id != user.user_id and not user.is_admin:
        raise PermissionError_("You do not have access to that report.")

    report = await db.scalar(
        select(Report).where(Report.audit_submission_id == audit.audit_submission_id)
    )
    if report is None:
        raise NotFoundError(
            "The report is not ready yet. Poll the job endpoint until it "
            "reports 'succeeded'."
        )

    snapshot = await db.scalar(
        select(SiteSnapshot).where(
            SiteSnapshot.audit_submission_id == audit.audit_submission_id
        )
    )

    signals = []
    site = SiteInfoOut(requested_url=audit.target_url, status="unknown")
    if snapshot is not None:
        site = SiteInfoOut(
            requested_url=snapshot.requested_url,
            final_url=snapshot.final_url,
            http_status=snapshot.http_status,
            fetch_duration_ms=snapshot.fetch_duration_ms,
            page_title=(snapshot.extracted or {}).get("title"),
            status=snapshot.status,
        )
        signals = [
            SignalOut(**{k: s[k] for k in ("key", "label", "ok", "value", "category")})
            for s in (snapshot.signals or {}).get("signals", [])
        ]

    return ReportOut(
        audit_id=audit.public_id,
        generated_at=report.created_at,
        scores=ScoresOut(
            overall=report.overall_score,
            visual=report.visual_score,
            technical=report.technical_score,
            business=report.business_score,
        ),
        executive_summary=report.executive_summary,
        framework=FrameworkOut(
            client_description=audit.client_description,
            user_description=audit.user_description,
            problem_description=audit.problem_description,
            value_creation_description=audit.value_creation_description,
            revenue_model_description=audit.revenue_model_description,
        ),
        site=site,
        findings=[FindingOut.model_validate(f) for f in report.findings],
        recommendations=[
            RecommendationOut.model_validate(r) for r in report.recommendations
        ],
        signals=signals,
        provider=report.provider,
        model=report.model,
    )
