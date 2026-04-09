from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import AttachmentArtifact, GuardrailFinding, RelevantFile, TicketAnalysis

TicketStatus = Literal["queued", "processing", "routed", "resolved", "failed"]


class TicketRecord(BaseModel):
    id: int
    title: str
    reporter_email: str | None = None
    description: str
    file_content: str = ""
    trace_id: str
    status: TicketStatus
    analysis: TicketAnalysis | None = None
    guardrail_findings: list[GuardrailFinding] = Field(default_factory=list)
    resolution_path: str | None = None
    relevant_files: list[RelevantFile] = Field(default_factory=list)
    attachments: list[AttachmentArtifact] = Field(default_factory=list)
    linear_issue_id: str | None = None
    linear_issue_url: str | None = None
    communicator_status: str | None = None
    communicator_reference: str | None = None
    assigned_team: str | None = None
    priority: str | None = None
    error_message: str | None = None
    resolution_note: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
