import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.schemas.tickets import TicketRecord


class TicketRepository:
    async def create_ticket(
        self,
        connection: aiosqlite.Connection,
        *,
        title: str,
        description: str,
        file_content: str,
    ) -> TicketRecord:
        now = self._utc_now()
        cursor = await connection.execute(
            """
            INSERT INTO tickets (
                title, description, file_content, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'queued', ?, ?)
            """,
            (title, description, file_content, now, now),
        )
        await connection.commit()
        return await self.get_ticket(connection, int(cursor.lastrowid))

    async def list_tickets(self, connection: aiosqlite.Connection) -> list[TicketRecord]:
        cursor = await connection.execute(
            "SELECT * FROM tickets ORDER BY datetime(created_at) DESC, id DESC"
        )
        rows = await cursor.fetchall()
        return [self._map_row(row) for row in rows]

    async def get_ticket(
        self, connection: aiosqlite.Connection, ticket_id: int
    ) -> TicketRecord | None:
        cursor = await connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._map_row(row)

    async def update_ticket(
        self,
        connection: aiosqlite.Connection,
        ticket_id: int,
        **fields: Any,
    ) -> TicketRecord | None:
        if not fields:
            return await self.get_ticket(connection, ticket_id)

        serializable_fields: dict[str, Any] = {}
        for key, value in fields.items():
            if key in {"analysis_json", "relevant_files_json"} and value is not None:
                serializable_fields[key] = json.dumps(value)
            else:
                serializable_fields[key] = value

        serializable_fields["updated_at"] = self._utc_now()
        assignments = ", ".join(f"{column} = ?" for column in serializable_fields)
        values = list(serializable_fields.values()) + [ticket_id]

        await connection.execute(
            f"UPDATE tickets SET {assignments} WHERE id = ?",
            values,
        )
        await connection.commit()
        return await self.get_ticket(connection, ticket_id)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _map_row(self, row: aiosqlite.Row) -> TicketRecord:
        analysis = json.loads(row["analysis_json"]) if row["analysis_json"] else None
        relevant_files = json.loads(row["relevant_files_json"]) if row["relevant_files_json"] else []

        return TicketRecord.model_validate(
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "file_content": row["file_content"],
                "status": row["status"],
                "analysis": analysis,
                "resolution_path": row["resolution_path"],
                "relevant_files": relevant_files,
                "linear_issue_id": row["linear_issue_id"],
                "linear_issue_url": row["linear_issue_url"],
                "assigned_team": row["assigned_team"],
                "priority": row["priority"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )


ticket_repository = TicketRepository()
