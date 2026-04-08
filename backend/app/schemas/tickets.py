from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import RelevantFile, TicketAnalysis

TicketStatus = Literal["queued", "processing", "routed", "failed"]


class TicketRecord(BaseModel):
    id: int
    title: str
    description: str
    file_content: str = ""
    status: TicketStatus
    analysis: TicketAnalysis | None = None
    resolution_path: str | None = None
    relevant_files: list[RelevantFile] = Field(default_factory=list)
    linear_issue_id: str | None = None
    linear_issue_url: str | None = None
    assigned_team: str | None = None
    priority: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
