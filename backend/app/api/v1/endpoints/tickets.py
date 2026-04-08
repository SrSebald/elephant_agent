from typing import Annotated

import aiosqlite
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_ticket_service
from app.core.database import get_connection
from app.schemas.tickets import TicketRecord
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get("", response_model=list[TicketRecord])
async def list_tickets(
    connection: aiosqlite.Connection = Depends(get_connection),
    service: TicketService = Depends(get_ticket_service),
):
    return await service.list_tickets(connection)


@router.post("", response_model=TicketRecord, status_code=status.HTTP_202_ACCEPTED)
async def create_ticket(
    background_tasks: BackgroundTasks,
    title: Annotated[str, Form(min_length=3, max_length=120)],
    description: Annotated[str, Form(min_length=10, max_length=5000)],
    files: Annotated[list[UploadFile] | None, File()] = None,
    connection: aiosqlite.Connection = Depends(get_connection),
    service: TicketService = Depends(get_ticket_service),
):
    try:
        ticket = await service.create_ticket_submission(
            connection=connection,
            title=title,
            description=description,
            files=files or [],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(service.process_ticket, ticket.id)
    return ticket
