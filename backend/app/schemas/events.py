from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventStage = Literal["ingest", "guardrails", "triage", "ticket", "notify", "communicator", "resolved", "system"]
EventLevel = Literal["info", "warning", "error"]


class TicketEvent(BaseModel):
    id: int
    ticket_id: int | None = None
    trace_id: str
    stage: EventStage
    level: EventLevel = "info"
    message: str
    payload: dict = Field(default_factory=dict)
    created_at: datetime


class ObservabilitySummary(BaseModel):
    total_tickets: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    stage_counts: dict[str, int] = Field(default_factory=dict)
    latest_event_at: datetime | None = None
