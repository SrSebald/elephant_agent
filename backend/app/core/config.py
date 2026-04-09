from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Elephant Agent API"
    api_v1_prefix: str = "/api/v1"
    database_path: str = "data/elephant_agent.db"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])
    frontend_origin: str = "http://localhost:3000"
    ecommerce_name: str = "Solidus Demo Store"
    ecommerce_platform: str = "Solidus"
    ecommerce_storefront_url: str | None = None
    ecommerce_admin_url: str | None = None
    ecommerce_support_email: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_site_url: str | None = None
    openai_app_name: str | None = None

    solidus_repo_url: str = "https://github.com/solidusio/solidus.git"
    solidus_repo_branch: str = "main"
    solidus_local_path: str = "data/solidus_repo"
    solidus_auto_clone: bool = True

    linear_api_key: str | None = None
    linear_default_team_id: str | None = None
    linear_default_team_name: str | None = None
    linear_core_team_id: str | None = None
    linear_admin_team_id: str | None = None
    linear_api_team_id: str | None = None

    resend_api_key: str | None = None
    resend_from_email: str = "tickets@example.com"
    core_team_email: str = "core@example.com"
    admin_team_email: str = "admin@example.com"
    api_team_email: str = "api@example.com"

    communicator_webhook_url: str | None = None
    core_comm_channel: str = "#solidus-core"
    admin_comm_channel: str = "#solidus-admin"
    api_comm_channel: str = "#solidus-api"

    allow_dry_run: bool = True

    max_attachments: int = 5
    max_upload_bytes: int = 5_000_000
    max_total_upload_bytes: int = 10_000_000

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_csv_or_list(cls, value: Any):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def solidus_repo_path(self) -> Path:
        configured_path = Path(self.solidus_local_path)
        if configured_path.is_absolute():
            return configured_path
        return BASE_DIR / configured_path


@lru_cache
def get_settings() -> Settings:
    return Settings()
