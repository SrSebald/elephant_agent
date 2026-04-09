from typing import Literal

from pydantic import BaseModel, Field


class RelevantFile(BaseModel):
    repository: str
    path: str
    url: str | None = None
    snippet: str = ""
    content_excerpt: str = ""
    score: float = 0.0


class GuardrailFinding(BaseModel):
    rule: str
    severity: Literal["info", "warning", "high"] = "warning"
    message: str


class AttachmentArtifact(BaseModel):
    filename: str
    kind: Literal["text", "image"]
    mime_type: str
    size_bytes: int
    sha256: str
    text_excerpt: str = ""
    prompt_injection_signals: list[str] = Field(default_factory=list)
    data_url: str | None = None

    def persisted_dict(self) -> dict:
        return self.model_dump(exclude={"data_url"})


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
    assigned_team: Literal["core", "admin", "api"] = "core"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    keywords: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    solidus_area: str = "solidus_core"
    next_steps: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    execution_mode: Literal["live", "dry-run"] = "live"
    guardrail_notes: list[str] = Field(default_factory=list)
