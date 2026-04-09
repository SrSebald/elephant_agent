import json
import logging

from app.core.database import connection_context
from app.repositories.event_repository import EventRepository, event_repository
from app.repositories.ticket_repository import TicketRepository, ticket_repository
from app.schemas.events import ObservabilitySummary, TicketEvent

logger = logging.getLogger("elephant_agent")


class ObservabilityService:
    def __init__(
        self,
        event_repo: EventRepository,
        ticket_repo: TicketRepository,
    ):
        self.event_repo = event_repo
        self.ticket_repo = ticket_repo

    async def record(
        self,
        *,
        ticket_id: int | None,
        trace_id: str,
        stage: str,
        message: str,
        level: str = "info",
        payload: dict | None = None,
    ) -> TicketEvent:
        event_payload = payload or {}
        logger.info(
            json.dumps(
                {
                    "ticket_id": ticket_id,
                    "trace_id": trace_id,
                    "stage": stage,
                    "level": level,
                    "message": message,
                    "payload": event_payload,
                }
            )
        )
        async with connection_context() as connection:
            return await self.event_repo.create_event(
                connection,
                ticket_id=ticket_id,
                trace_id=trace_id,
                stage=stage,
                level=level,
                message=message,
                payload=event_payload,
            )

    async def list_ticket_events(self, ticket_id: int) -> list[TicketEvent]:
        async with connection_context() as connection:
            return await self.event_repo.list_events_for_ticket(connection, ticket_id)

    async def summary(self) -> ObservabilitySummary:
        async with connection_context() as connection:
            tickets = await self.ticket_repo.list_tickets(connection)
            status_counts = await self.ticket_repo.status_counts(connection)
            return await self.event_repo.observability_summary(
                connection,
                total_tickets=len(tickets),
                status_counts=status_counts,
            )


observability_service = ObservabilityService(event_repository, ticket_repository)

