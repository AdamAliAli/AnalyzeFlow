from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BusinessProfileCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    website_url: str | None = None
    industry: str | None = Field(
        default=None,
        description="Industry name or slug. Unknown values are stored as free text.",
    )
    business_description: str | None = None


class BusinessProfileUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=200)
    website_url: str | None = None
    industry: str | None = None
    business_description: str | None = None


class BusinessProfileOut(ORMModel):
    business_profile_id: int
    business_name: str
    website_url: str | None
    industry: str | None = None
    business_description: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, profile) -> "BusinessProfileOut":
        return cls(
            business_profile_id=profile.business_profile_id,
            business_name=profile.business_name,
            website_url=profile.website_url,
            industry=profile.industry_label,
            business_description=profile.business_description,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
