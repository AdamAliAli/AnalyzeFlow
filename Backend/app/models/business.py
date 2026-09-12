from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class BusinessProfile(Base, TimestampMixin):
    __tablename__ = "business_profiles"

    business_profile_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry_id: Mapped[int | None] = mapped_column(
        ForeignKey("industries.industry_id", ondelete="SET NULL"), nullable=True
    )
    # Free-text fallback when the user's industry isn't in the dropdown.
    industry_other: Mapped[str | None] = mapped_column(String(150), nullable=True)
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="business_profiles")  # noqa: F821
    industry: Mapped["Industry | None"] = relationship(lazy="joined")  # noqa: F821
    audits: Mapped[list["AuditSubmission"]] = relationship(  # noqa: F821
        back_populates="business_profile", cascade="all, delete-orphan"
    )

    @property
    def industry_label(self) -> str | None:
        return self.industry.name if self.industry else self.industry_other
