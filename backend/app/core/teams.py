from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class TeamConfig:
    slug: str
    display_name: str
    linear_team_id: str | None
    email: str
    repo_hints: tuple[str, ...]
    keywords: tuple[str, ...]


def get_team_catalog(settings: Settings) -> dict[str, TeamConfig]:
    return {
        "backend": TeamConfig(
            slug="backend",
            display_name="Backend",
            linear_team_id=settings.linear_backend_team_id,
            email=settings.backend_team_email,
            repo_hints=("api", "services", "worker", "backend"),
            keywords=("api", "database", "queue", "timeout", "500", "exception", "worker"),
        ),
        "frontend": TeamConfig(
            slug="frontend",
            display_name="Frontend",
            linear_team_id=settings.linear_frontend_team_id,
            email=settings.frontend_team_email,
            repo_hints=("web", "app", "frontend", "ui"),
            keywords=("ui", "browser", "page", "render", "react", "button", "frontend"),
        ),
        "infra": TeamConfig(
            slug="infra",
            display_name="Infra",
            linear_team_id=settings.linear_infra_team_id,
            email=settings.infra_team_email,
            repo_hints=("infra", "deploy", "ops", "terraform"),
            keywords=("deploy", "config", "dns", "kubernetes", "terraform", "docker", "infra"),
        ),
    }
