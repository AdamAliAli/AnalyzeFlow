"""String enums shared by models, schemas and the AI contract.

These values are part of the public API surface. The front end and the AI
provider both depend on the exact strings below - change them only with a
migration and a note to the team.
"""

from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class AuditStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobStage(StrEnum):
    """Coarse progress steps, surfaced to the front end's progress screen."""

    QUEUED = "queued"
    FETCHING_SITE = "fetching_site"
    EXTRACTING_SIGNALS = "extracting_signals"
    RUNNING_ANALYSIS = "running_analysis"
    SAVING_REPORT = "saving_report"
    DONE = "done"


class FindingCategory(StrEnum):
    """The three pillars of the report the product promises."""

    VISUAL = "visual"       # design, layout, UX, accessibility
    TECHNICAL = "technical" # backend ops, performance, SEO, security headers
    BUSINESS = "business"   # positioning, value prop, conversion, monetisation


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EffortLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImpactLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SnapshotStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"       # fetched, but some resources failed
    UNREACHABLE = "unreachable"
    BLOCKED = "blocked"       # robots.txt / 403 / bot wall
