from pydantic import BaseModel, Field


class EcommerceContext(BaseModel):
    name: str
    platform: str
    storefront_url: str | None = None
    admin_url: str | None = None
    support_email: str | None = None
    codebase_repo_url: str
    codebase_branch: str


class LinearTeamTarget(BaseModel):
    slug: str
    display_name: str
    configured_team_id: str | None = None
    effective_team_id: str | None = None
    effective_team_name: str | None = None


class LinearContext(BaseModel):
    connected: bool
    mode: str
    default_team_id: str | None = None
    default_team_name: str | None = None
    targets: list[LinearTeamTarget] = Field(default_factory=list)


class AppContext(BaseModel):
    ecommerce: EcommerceContext
    linear: LinearContext
