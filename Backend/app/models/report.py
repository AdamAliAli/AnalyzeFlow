"""The generated report: scores, findings, recommendations."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.models.enums import FindingCategory


class Report(Base, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "overall_score BETWEEN 0 AND 100", name="chk_reports_overall_score"
        ),
    )

    report_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audit_submission_id: Mapped[int] = mapped_column(
        ForeignKey("audit_submissions.audit_submission_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Headline numbers. These feed the three metric cards already designed on
    # the homepage hero (UX Score / Conversion Potential / Business Clarity).
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visual_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    technical_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    business_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Provenance - which analyzer produced this, so results stay auditable
    # when the AI teammate swaps providers or models.
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    analysis_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    audit: Mapped["AuditSubmission"] = relationship(back_populates="report")  # noqa: F821
    findings: Mapped[list["ReportFinding"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReportFinding.display_order",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Recommendation.priority",
    )


class ReportFinding(Base, CreatedAtMixin):
    """One observed problem. Grouped into the report's three sections."""

    __tablename__ = "report_findings"
    __table_args__ = (
        CheckConstraint(
            "category IN ('visual','technical','business')",
            name="chk_report_findings_category",
        ),
        CheckConstraint(
            "severity IN ('critical','high','medium','low','info')",
            name="chk_report_findings_severity",
        ),
        Index("idx_report_findings_report_id", "report_id"),
    )

    report_finding_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.report_id", ondelete="CASCADE"), nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(20), nullable=False, default=FindingCategory.VISUAL
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # What in the page triggered this - a selector, a header name, a metric.
    # Keeps the report defensible instead of hand-wavy.
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional link back to the wizard challenge this finding explains.
    challenge_id: Mapped[int | None] = mapped_column(
        ForeignKey("challenges.challenge_id", ondelete="SET NULL"), nullable=True
    )

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    report: Mapped["Report"] = relationship(back_populates="findings")


class Recommendation(Base, TimestampMixin):
    """An action to take. Extended from the team's original table."""

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "priority IS NULL OR priority BETWEEN 1 AND 5",
            name="chk_recommendations_priority",
        ),
        CheckConstraint(
            "category IN ('visual','technical','business')",
            name="chk_recommendations_category",
        ),
        CheckConstraint(
            "effort IN ('low','medium','high')", name="chk_recommendations_effort"
        ),
        CheckConstraint(
            "impact IN ('low','medium','high')", name="chk_recommendations_impact"
        ),
        Index("idx_recommendations_report_id", "report_id"),
    )

    recommendation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.report_id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="business")
    priority: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    effort: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    impact: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")

    # Concrete first step, so the report is actionable rather than advisory.
    first_step: Mapped[str | None] = mapped_column(Text, nullable=True)

    report_finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("report_findings.report_finding_id", ondelete="SET NULL"),
        nullable=True,
    )

    report: Mapped["Report"] = relationship(back_populates="recommendations")
