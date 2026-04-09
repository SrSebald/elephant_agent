from contextlib import asynccontextmanager

import aiosqlite

from app.core.config import BASE_DIR, get_settings

CREATE_TICKETS_TABLE = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    file_content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',
    analysis_json TEXT,
    resolution_path TEXT,
    relevant_files_json TEXT,
    linear_issue_id TEXT,
    linear_issue_url TEXT,
    assigned_team TEXT,
    priority TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


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
        await connection.execute(CREATE_TICKETS_TABLE)
        await connection.commit()


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
