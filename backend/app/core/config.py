from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Elephant Agent API"
    api_v1_prefix: str = "/api/v1"
    database_path: str = "data/elephant_agent.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    frontend_origin: str = "http://localhost:3000"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    github_token: str | None = None
    github_owner: str | None = None
    github_repositories: list[str] = Field(default_factory=lambda: ["api", "web", "infra"])

    linear_api_key: str | None = None
    linear_backend_team_id: str | None = None
    linear_frontend_team_id: str | None = None
    linear_infra_team_id: str | None = None

    resend_api_key: str | None = None
    resend_from_email: str = "tickets@example.com"
    backend_team_email: str = "backend@example.com"
    frontend_team_email: str = "frontend@example.com"
    infra_team_email: str = "infra@example.com"

    allow_dry_run: bool = True

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", "github_repositories", mode="before")
    @classmethod
    def parse_csv_or_list(cls, value: Any):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
