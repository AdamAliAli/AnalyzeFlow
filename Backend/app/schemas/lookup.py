from app.schemas.common import ORMModel


class LookupItem(ORMModel):
    id: int
    name: str
    slug: str
    description: str | None = None


class LookupBundle(ORMModel):
    """Everything the wizard needs to render its fixed choices, in one call."""

    industries: list[LookupItem]
    goals: list[LookupItem]
    challenges: list[LookupItem]
    business_stages: list[LookupItem]
