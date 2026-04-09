from typing import Annotated

import aiosqlite
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.dependencies import get_ticket_service
from app.core.database import get_connection
from app.schemas.events import ObservabilitySummary, TicketEvent
from app.schemas.tickets import TicketRecord
from app.services.ticket_service import TicketService

router = APIRouter()


class ResolveTicketPayload(BaseModel):
    resolution_note: str = "Resolved manually from the dashboard."


@router.get("", response_model=list[TicketRecord])
async def list_tickets(
    connection: aiosqlite.Connection = Depends(get_connection),
    service: TicketService = Depends(get_ticket_service),
):
    return await service.list_tickets(connection)


@router.get("/observability/summary", response_model=ObservabilitySummary)
async def observability_summary(
    service: TicketService = Depends(get_ticket_service),
):
    return await service.observability_summary()


@router.get("/{ticket_id}/events", response_model=list[TicketEvent])
async def ticket_events(
    ticket_id: int,
    service: TicketService = Depends(get_ticket_service),
):
    return await service.list_events(ticket_id)


@router.post("", response_model=TicketRecord, status_code=status.HTTP_202_ACCEPTED)
async def create_ticket(
    background_tasks: BackgroundTasks,
    title: Annotated[str, Form(min_length=3, max_length=120)],
    description: Annotated[str, Form(min_length=10, max_length=5000)],
    reporter_email: Annotated[str | None, Form(max_length=255)] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    connection: aiosqlite.Connection = Depends(get_connection),
    service: TicketService = Depends(get_ticket_service),
):
    try:
        ticket = await service.create_ticket_submission(
            connection=connection,
            title=title,
            reporter_email=reporter_email,
            description=description,
            files=files or [],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(service.process_ticket, ticket.id)
    return ticket


@router.post("/{ticket_id}/resolve", response_model=TicketRecord)
async def resolve_ticket(
    ticket_id: int,
    payload: ResolveTicketPayload,
    service: TicketService = Depends(get_ticket_service),
):
    try:
        return await service.resolve_ticket(ticket_id, payload.resolution_note)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
