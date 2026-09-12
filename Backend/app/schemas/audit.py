from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class AuditCreate(BaseModel):
    """Exactly what the 4-step wizard collects, in one POST.

    Lookup fields accept either the display label the front end currently
    sends ("Low Online Visibility") or the stable slug
    ("low_online_visibility"). The backend resolves both.
    """

    # Step 1
    business_name: str = Field(min_length=1, max_length=200)
    website_url: str = Field(min_length=3, description="The site to analyse.")
    industry: str | None = None

    # Step 2
    goal: str = Field(description="Label or slug, e.g. 'Increase Sales'")

    # Step 3
    challenges: list[str] = Field(
        min_length=1, description="One or more labels or slugs."
    )

    # Step 4
    business_stage: str = Field(description="Label or slug, e.g. 'Startup'")

    business_description: str | None = None
    business_profile_id: int | None = Field(
        default=None,
        description="Reuse an existing profile instead of creating a new one.",
    )

    @field_validator("website_url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A website URL is required.")
        return value

    @field_validator("challenges")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        seen, out = set(), []
        for item in value:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item.strip())
        if not out:
            raise ValueError("Select at least one challenge.")
        return out


class JobOut(ORMModel):
    job_id: str = Field(description="Public job id - poll this.")
    status: str
    stage: str
    progress: int = Field(ge=0, le=100)
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @classmethod
    def from_model(cls, job) -> "JobOut":
        return cls(
            job_id=job.public_id,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            error_code=job.error_code,
            error_message=job.error_message,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )


class AuditOut(ORMModel):
    audit_id: str
    status: str
    target_url: str
    business_name: str
    industry: str | None
    goal: str
    challenges: list[str]
    business_stage: str
    submitted_at: datetime
    has_report: bool = False

    @classmethod
    def from_model(cls, audit, has_report: bool = False) -> "AuditOut":
        return cls(
            audit_id=audit.public_id,
            status=audit.status,
            target_url=audit.target_url,
            business_name=audit.business_profile.business_name,
            industry=audit.business_profile.industry_label,
            goal=audit.goal.name,
            challenges=[c.name for c in audit.challenges],
            business_stage=audit.business_stage.name,
            submitted_at=audit.submitted_at,
            has_report=has_report,
        )


class AuditCreated(BaseModel):
    """Returned immediately from POST /audits - the report is not ready yet."""

    audit: AuditOut
    job: JobOut
    poll_url: str
