from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class TeamConfig:
    slug: str
    display_name: str
    linear_team_id: str | None
    email: str
    communicator_channel: str
    repo_hints: tuple[str, ...]
    keywords: tuple[str, ...]


def get_team_catalog(settings: Settings) -> dict[str, TeamConfig]:
    return {
        "core": TeamConfig(
            slug="core",
            display_name="Solidus Core",
            linear_team_id=settings.linear_core_team_id,
            email=settings.core_team_email,
            communicator_channel=settings.core_comm_channel,
            repo_hints=("core", "solidus_core", "models", "mailers", "calculators", "promotions"),
            keywords=("order", "checkout", "payment", "shipment", "promotion", "tax", "inventory"),
        ),
        "admin": TeamConfig(
            slug="admin",
            display_name="Solidus Admin",
            linear_team_id=settings.linear_admin_team_id,
            email=settings.admin_team_email,
            communicator_channel=settings.admin_comm_channel,
            repo_hints=("backend", "solidus_backend", "admin", "dashboard"),
            keywords=("admin", "backend", "ui", "dashboard", "page", "form", "button"),
        ),
        "api": TeamConfig(
            slug="api",
            display_name="Solidus API",
            linear_team_id=settings.linear_api_team_id,
            email=settings.api_team_email,
            communicator_channel=settings.api_comm_channel,
            repo_hints=("api", "solidus_api", "controllers", "serializers"),
            keywords=("api", "endpoint", "json", "serializer", "controller", "token"),
        ),
    }
