from typing import Literal

from pydantic import BaseModel, Field


class RelevantFile(BaseModel):
    repository: str
    path: str
    url: str | None = None
    snippet: str = ""
    content_excerpt: str = ""


class ExtractionSignal(BaseModel):
    category: Literal["bug", "incident", "config"] = "bug"
    keywords: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)


class TicketAnalysis(BaseModel):
    category: Literal["bug", "incident", "config"] = "bug"
    summary: str
    diagnosis: str
    resolution_path: str
    assigned_team: Literal["backend", "frontend", "infra"] = "backend"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    keywords: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    execution_mode: Literal["live", "dry-run"] = "live"
