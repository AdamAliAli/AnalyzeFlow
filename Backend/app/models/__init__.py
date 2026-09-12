"""Import every model here so Alembic's autogenerate sees them all."""

from app.db.base import Base
from app.models.audit import AuditChallenge, AuditSubmission
from app.models.business import BusinessProfile
from app.models.case_study import CaseStudy
from app.models.enums import (
    AuditStatus,
    EffortLevel,
    FindingCategory,
    ImpactLevel,
    JobStage,
    JobStatus,
    Severity,
    SnapshotStatus,
    UserRole,
)
from app.models.job import AnalysisJob
from app.models.lookup import BusinessStage, Challenge, Goal, Industry
from app.models.report import Recommendation, Report, ReportFinding
from app.models.snapshot import SiteSnapshot
from app.models.user import RefreshToken, User

__all__ = [
    "AnalysisJob",
    "AuditChallenge",
    "AuditStatus",
    "AuditSubmission",
    "Base",
    "BusinessProfile",
    "BusinessStage",
    "CaseStudy",
    "Challenge",
    "EffortLevel",
    "FindingCategory",
    "Goal",
    "ImpactLevel",
    "Industry",
    "JobStage",
    "JobStatus",
    "Recommendation",
    "RefreshToken",
    "Report",
    "ReportFinding",
    "Severity",
    "SiteSnapshot",
    "SnapshotStatus",
    "User",
    "UserRole",
]
