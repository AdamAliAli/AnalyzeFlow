from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CaseStudy(Base, TimestampMixin):
    """Admin-authored marketing content. Not tied to a user's audit.

    Columns reconcile the two conflicting versions in the team's docs: the
    SQL draft (title/industry/summary/content) and the report's Section 10 ERD
    (ClientType/UserType/Goal/ValueProposition/KeyInsight). Both are kept.
    """

    __tablename__ = "case_studies"
    __table_args__ = (Index("idx_case_studies_published", "is_published"),)

    case_study_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    industry_id: Mapped[int | None] = mapped_column(
        ForeignKey("industries.industry_id", ondelete="SET NULL"), nullable=True
    )
    industry_label: Mapped[str | None] = mapped_column(String(150), nullable=True)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # markdown

    # The five-question framework, worked through for this example.
    client_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    problem: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_proposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_insight: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
