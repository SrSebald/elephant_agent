from fastapi import APIRouter, Depends

from app.api.dependencies import get_ticket_service
from app.schemas.context import AppContext
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get("", response_model=AppContext)
async def app_context(
    service: TicketService = Depends(get_ticket_service),
):
    return service.app_context()
