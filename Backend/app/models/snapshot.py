"""What we fetched from the target website, frozen for reproducibility."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin
from app.models.enums import SnapshotStatus


class SiteSnapshot(Base, CreatedAtMixin):
    __tablename__ = "site_snapshots"

    site_snapshot_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audit_submission_id: Mapped[int] = mapped_column(
        ForeignKey("audit_submissions.audit_submission_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    requested_url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SnapshotStatus.OK
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    fetch_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Structured extraction (title, meta, headings, links, images, forms...).
    # Shape is defined by app/services/scraper/extractor.py -> PageContent.
    extracted: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Deterministic rule-based measurements computed from `extracted`.
    # Shape defined by app/services/scraper/signals.py -> SiteSignals.
    signals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Plain text handed to the AI provider. Capped; see scraper settings.
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    audit: Mapped["AuditSubmission"] = relationship(back_populates="snapshot")  # noqa: F821
