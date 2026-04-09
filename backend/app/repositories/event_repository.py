import json
from datetime import datetime, timezone

import aiosqlite

from app.schemas.events import ObservabilitySummary, TicketEvent


class EventRepository:
    async def create_event(
        self,
        connection: aiosqlite.Connection,
        *,
        ticket_id: int | None,
        trace_id: str,
        stage: str,
        level: str,
        message: str,
        payload: dict | None = None,
    ) -> TicketEvent:
        now = self._utc_now()
        cursor = await connection.execute(
            """
            INSERT INTO ticket_events (
                ticket_id, trace_id, stage, level, message, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, trace_id, stage, level, message, json.dumps(payload or {}), now),
        )
        await connection.commit()
        return await self.get_event(connection, int(cursor.lastrowid))

    async def get_event(self, connection: aiosqlite.Connection, event_id: int) -> TicketEvent:
        cursor = await connection.execute(
            "SELECT * FROM ticket_events WHERE id = ?",
            (event_id,),
        )
        row = await cursor.fetchone()
        return self._map_row(row)

    async def list_events_for_ticket(
        self,
        connection: aiosqlite.Connection,
        ticket_id: int,
    ) -> list[TicketEvent]:
        cursor = await connection.execute(
            "SELECT * FROM ticket_events WHERE ticket_id = ? ORDER BY datetime(created_at) ASC, id ASC",
            (ticket_id,),
        )
        rows = await cursor.fetchall()
        return [self._map_row(row) for row in rows]

    async def stage_counts(self, connection: aiosqlite.Connection) -> dict[str, int]:
        cursor = await connection.execute(
            "SELECT stage, COUNT(*) as count FROM ticket_events GROUP BY stage"
        )
        rows = await cursor.fetchall()
        return {row["stage"]: row["count"] for row in rows}

    async def latest_event_at(self, connection: aiosqlite.Connection) -> datetime | None:
        cursor = await connection.execute(
            "SELECT created_at FROM ticket_events ORDER BY datetime(created_at) DESC, id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return None if row is None else datetime.fromisoformat(row["created_at"])

    async def observability_summary(
        self,
        connection: aiosqlite.Connection,
        *,
        total_tickets: int,
        status_counts: dict[str, int],
    ) -> ObservabilitySummary:
        return ObservabilitySummary(
            total_tickets=total_tickets,
            status_counts=status_counts,
            stage_counts=await self.stage_counts(connection),
            latest_event_at=await self.latest_event_at(connection),
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _map_row(self, row: aiosqlite.Row) -> TicketEvent:
        return TicketEvent.model_validate(
            {
                "id": row["id"],
                "ticket_id": row["ticket_id"],
                "trace_id": row["trace_id"],
                "stage": row["stage"],
                "level": row["level"],
                "message": row["message"],
                "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
                "created_at": row["created_at"],
            }
        )


event_repository = EventRepository()
