from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FindingOut(ORMModel):
    category: str
    severity: str
    title: str
    description: str
    evidence: str | None = None


class RecommendationOut(ORMModel):
    title: str
    description: str
    category: str
    priority: int | None
    effort: str
    impact: str
    first_step: str | None = None


class ScoresOut(BaseModel):
    overall: int
    visual: int
    technical: int
    business: int


class FrameworkOut(BaseModel):
    client_description: str | None = None
    user_description: str | None = None
    problem_description: str | None = None
    value_creation_description: str | None = None
    revenue_model_description: str | None = None


class SignalOut(BaseModel):
    key: str
    label: str
    ok: bool
    value: str
    category: str


class SiteInfoOut(BaseModel):
    requested_url: str
    final_url: str | None = None
    http_status: int | None = None
    fetch_duration_ms: int | None = None
    page_title: str | None = None
    status: str


class ReportOut(BaseModel):
    audit_id: str
    generated_at: datetime
    scores: ScoresOut
    executive_summary: str
    framework: FrameworkOut
    site: SiteInfoOut
    findings: list[FindingOut] = Field(default_factory=list)
    recommendations: list[RecommendationOut] = Field(default_factory=list)
    signals: list[SignalOut] = Field(default_factory=list)
    provider: str
    model: str | None = None


class CaseStudyOut(ORMModel):
    case_study_id: int
    slug: str
    title: str
    industry_label: str | None
    summary: str
    content: str
    client_type: str | None
    user_type: str | None
    problem: str | None
    value_proposition: str | None
    revenue_model: str | None
    key_insight: str | None
    created_at: datetime


class CaseStudySummaryOut(ORMModel):
    case_study_id: int
    slug: str
    title: str
    industry_label: str | None
    summary: str
    key_insight: str | None
