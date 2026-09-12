"""THE AI INTEGRATION CONTRACT.

This file is the boundary between the backend (our responsibility) and the AI
integration (the teammate's responsibility). Nothing else in the backend needs
to change when the AI work lands.

To plug in a real model, the AI teammate:

    1. Creates app/services/ai/<name>_provider.py
    2. Implements `AnalyzerProvider` - one async method, `analyze()`
    3. Registers it in app/services/ai/registry.py
    4. Sets AI_PROVIDER=<name> in .env

They receive a fully-populated `AnalysisInput` and must return a valid
`AnalysisOutput`. They never touch the database, HTTP layer, or job queue.

Both models are Pydantic, so a provider can hand the JSON schema straight to a
model's structured-output / tool-calling feature and validate the reply with
`AnalysisOutput.model_validate_json(...)`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator

from app.models.enums import EffortLevel, FindingCategory, ImpactLevel, Severity

# ---------------------------------------------------------------------------
# INPUT - what the provider is given
# ---------------------------------------------------------------------------


class BusinessContext(BaseModel):
    """What the user told us in the wizard."""

    business_name: str
    website_url: str
    industry: str | None = None
    goal: str = Field(description="Wizard step 2, e.g. 'Increase Sales'")
    challenges: list[str] = Field(
        default_factory=list,
        description="Wizard step 3, e.g. ['Low Online Visibility', 'Low Sales']",
    )
    business_stage: str = Field(description="Wizard step 4, e.g. 'Startup'")
    business_description: str | None = None


class SiteEvidence(BaseModel):
    """What we measured on the live website. All facts, no opinions."""

    final_url: str
    http_status: int
    fetch_duration_ms: int
    page_title: str = ""
    meta_description: str = ""
    headings_h1: list[str] = Field(default_factory=list)
    headings_h2: list[str] = Field(default_factory=list)
    visible_text: str = Field(
        default="", description="Cleaned page text, capped at ~20k characters"
    )
    cta_labels: list[str] = Field(default_factory=list)
    form_count: int = 0
    image_count: int = 0
    images_missing_alt: int = 0
    social_links: list[str] = Field(default_factory=list)
    detected_platform: list[str] = Field(default_factory=list)
    detected_analytics: list[str] = Field(default_factory=list)

    rule_signals: list[dict] = Field(
        default_factory=list,
        description=(
            "Deterministic checks already run by the backend. Each item is "
            "{key,label,ok,value,category,weight}. Do NOT re-derive these - "
            "build on them and explain what they mean for this business."
        ),
    )
    rule_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Rule-based baseline: visual/technical/business/overall, 0-100",
    )


class AnalysisInput(BaseModel):
    business: BusinessContext
    site: SiteEvidence
    locale: str = "en"
    max_findings_per_category: int = 5
    max_recommendations: int = 8


# ---------------------------------------------------------------------------
# OUTPUT - what the provider must return
# ---------------------------------------------------------------------------


class FrameworkAnswers(BaseModel):
    """The five framework questions, inferred from the website.

    These fill audit_submissions.*_description, which the wizard never asks
    for. If the website gives no basis for an answer, leave it None rather
    than inventing one.
    """

    client_description: str | None = None
    user_description: str | None = None
    problem_description: str | None = None
    value_creation_description: str | None = None
    revenue_model_description: str | None = None


class Finding(BaseModel):
    category: FindingCategory
    severity: Severity
    title: str = Field(max_length=200)
    description: str = Field(
        description="2-4 sentences: what is wrong and why it costs this business."
    )
    evidence: str | None = Field(
        default=None,
        description=(
            "What on the page proves this - a heading, a missing header, a "
            "measured number. Findings without evidence get dropped."
        ),
    )
    related_challenge: str | None = Field(
        default=None,
        description="Slug of the wizard challenge this explains, if any.",
    )


class RecommendationOut(BaseModel):
    category: FindingCategory
    title: str = Field(max_length=200)
    description: str
    priority: int = Field(ge=1, le=5, description="1 = do this first")
    effort: EffortLevel = EffortLevel.MEDIUM
    impact: ImpactLevel = ImpactLevel.MEDIUM
    first_step: str | None = Field(
        default=None, description="One concrete action to take today."
    )


class Scores(BaseModel):
    overall: int = Field(ge=0, le=100)
    visual: int = Field(ge=0, le=100)
    technical: int = Field(ge=0, le=100)
    business: int = Field(ge=0, le=100)


class AnalysisOutput(BaseModel):
    scores: Scores
    executive_summary: str = Field(
        description="3-5 sentences the business owner reads first."
    )
    framework: FrameworkAnswers = Field(default_factory=FrameworkAnswers)
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[RecommendationOut] = Field(default_factory=list)

    provider: str = "unknown"
    model: str | None = None

    @field_validator("findings")
    @classmethod
    def _drop_unevidenced(cls, findings: list[Finding]) -> list[Finding]:
        """A report is only credible if every claim points at something."""
        return [f for f in findings if f.evidence or f.description]

    @field_validator("recommendations")
    @classmethod
    def _sort_by_priority(
        cls, recs: list[RecommendationOut]
    ) -> list[RecommendationOut]:
        return sorted(recs, key=lambda r: r.priority)


# ---------------------------------------------------------------------------
# THE INTERFACE
# ---------------------------------------------------------------------------


class AnalyzerError(Exception):
    """Raised by a provider when analysis cannot be completed."""

    def __init__(self, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


@runtime_checkable
class AnalyzerProvider(Protocol):
    """Implement this and you are done. Nothing else in the backend changes."""

    name: str

    async def analyze(self, payload: AnalysisInput) -> AnalysisOutput:
        """Produce the report body.

        Must raise AnalyzerError on failure (retryable=False for bad API keys
        or invalid requests, True for timeouts and rate limits). Must not
        raise anything else; the job runner treats unknown exceptions as
        non-retryable bugs.
        """
        ...
