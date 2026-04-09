from contextlib import asynccontextmanager

import aiosqlite

from app.core.config import BASE_DIR, get_settings

TICKET_COLUMNS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "title": "TEXT NOT NULL",
    "reporter_email": "TEXT",
    "description": "TEXT NOT NULL",
    "file_content": "TEXT NOT NULL DEFAULT ''",
    "trace_id": "TEXT NOT NULL DEFAULT ''",
    "status": "TEXT NOT NULL DEFAULT 'queued'",
    "analysis_json": "TEXT",
    "guardrails_json": "TEXT",
    "resolution_path": "TEXT",
    "relevant_files_json": "TEXT",
    "attachments_json": "TEXT",
    "linear_issue_id": "TEXT",
    "linear_issue_url": "TEXT",
    "communicator_status": "TEXT",
    "communicator_reference": "TEXT",
    "assigned_team": "TEXT",
    "priority": "TEXT",
    "error_message": "TEXT",
    "resolution_note": "TEXT",
    "resolved_at": "TEXT",
    "created_at": "TEXT NOT NULL",
    "updated_at": "TEXT NOT NULL",
}

EVENT_COLUMNS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "ticket_id": "INTEGER",
    "trace_id": "TEXT NOT NULL",
    "stage": "TEXT NOT NULL",
    "level": "TEXT NOT NULL DEFAULT 'info'",
    "message": "TEXT NOT NULL",
    "payload_json": "TEXT",
    "created_at": "TEXT NOT NULL",
}


class Database:
    def __init__(self):
        settings = get_settings()
        self.db_path = BASE_DIR / settings.database_path

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as connection:
            await self._ensure_schema(connection)

    async def connect(self) -> aiosqlite.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(self.db_path)
        connection.row_factory = aiosqlite.Row
        await self._ensure_schema(connection)
        return connection

    async def _ensure_schema(self, connection: aiosqlite.Connection) -> None:
        await self._ensure_table(connection, "tickets", TICKET_COLUMNS)
        await self._ensure_table(connection, "ticket_events", EVENT_COLUMNS)
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket_created ON ticket_events(ticket_id, created_at)"
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ticket_events_stage_created ON ticket_events(stage, created_at)"
        )
        await connection.commit()

    async def _ensure_table(
        self,
        connection: aiosqlite.Connection,
        table_name: str,
        columns: dict[str, str],
    ) -> None:
        column_sql = ", ".join(f"{column} {definition}" for column, definition in columns.items())
        await connection.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({column_sql})")

        cursor = await connection.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {row[1] for row in await cursor.fetchall()}
        for column, definition in columns.items():
            if column in existing_columns:
                continue
            await connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}")


database = Database()


@asynccontextmanager
async def connection_context():
    connection = await database.connect()
    try:
        yield connection
    finally:
        await connection.close()


async def get_connection():
    async with connection_context() as connection:
        yield connection
