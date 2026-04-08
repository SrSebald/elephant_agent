from collections.abc import Sequence

import aiosqlite
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.database import connection_context
from app.graph import build_ticket_graph
from app.repositories.ticket_repository import TicketRepository, ticket_repository
from app.schemas.tickets import TicketRecord
from app.services.email import EmailService
from app.services.github import GitHubService
from app.services.linear import LinearService
from app.services.llm import LLMService

ALLOWED_EXTENSIONS = {".txt", ".md", ".log"}


class TicketService:
    def __init__(self, repository: TicketRepository):
        self.repository = repository
        self.settings = get_settings()
        self.llm_service = LLMService(self.settings)
        self.github_service = GitHubService(self.settings)
        self.linear_service = LinearService(self.settings)
        self.email_service = EmailService(self.settings)
        self.workflow = build_ticket_graph(
            llm_service=self.llm_service,
            github_service=self.github_service,
            linear_service=self.linear_service,
            email_service=self.email_service,
        )

    async def list_tickets(self, connection: aiosqlite.Connection) -> list[TicketRecord]:
        return await self.repository.list_tickets(connection)

    async def create_ticket_submission(
        self,
        *,
        connection: aiosqlite.Connection,
        title: str,
        description: str,
        files: Sequence[UploadFile],
    ) -> TicketRecord:
        clean_title = title.strip()
        clean_description = description.strip()
        if not clean_title:
            raise ValueError("Title cannot be empty.")
        if not clean_description:
            raise ValueError("Description cannot be empty.")

        file_content = await self._read_uploads(files)
        return await self.repository.create_ticket(
            connection,
            title=clean_title,
            description=clean_description,
            file_content=file_content,
        )

    async def process_ticket(self, ticket_id: int) -> None:
        async with connection_context() as connection:
            ticket = await self.repository.get_ticket(connection, ticket_id)
            if ticket is None:
                return
            await self.repository.update_ticket(
                connection,
                ticket_id,
                status="processing",
                error_message=None,
            )

        try:
            result = await self.workflow.ainvoke(
                self._build_state(ticket),
                {"configurable": {"thread_id": str(ticket_id)}},
            )
        except Exception as exc:
            async with connection_context() as connection:
                await self.repository.update_ticket(
                    connection,
                    ticket_id,
                    status="failed",
                    error_message=str(exc),
                )
            return

        async with connection_context() as connection:
            await self.repository.update_ticket(
                connection,
                ticket_id,
                status=result["status"],
                analysis_json=result.get("analysis"),
                resolution_path=result.get("resolution_path"),
                relevant_files_json=result.get("relevant_files"),
                linear_issue_id=result.get("linear_issue_id"),
                linear_issue_url=result.get("linear_issue_url"),
                assigned_team=result.get("assigned_team"),
                priority=result.get("priority"),
                error_message=result.get("error_message"),
            )

    async def _read_uploads(self, files: Sequence[UploadFile]) -> str:
        rendered_files: list[str] = []
        for upload in files:
            if not upload.filename:
                continue
            extension = self._extension(upload.filename)
            if extension not in ALLOWED_EXTENSIONS:
                raise ValueError("Only .txt, .md, and .log files are allowed in the MVP.")
            content = await upload.read()
            decoded = content.decode("utf-8", errors="ignore").strip()
            rendered_files.append(f"### {upload.filename}\n{decoded}")
        return "\n\n".join(rendered_files)

    @staticmethod
    def _extension(filename: str) -> str:
        lowered = filename.lower()
        for extension in ALLOWED_EXTENSIONS:
            if lowered.endswith(extension):
                return extension
        return ""

    @staticmethod
    def _build_state(ticket: TicketRecord) -> dict:
        return {
            "ticket_id": ticket.id,
            "title": ticket.title,
            "report_text": f"{ticket.title}\n\n{ticket.description}",
            "file_content": ticket.file_content,
            "analysis": None,
            "resolution_path": "",
            "relevant_files": [],
            "assigned_team": "backend",
            "priority": "medium",
            "linear_issue_id": None,
            "linear_issue_url": None,
            "email_sent": False,
            "status": "processing",
            "error_message": None,
        }


ticket_service = TicketService(ticket_repository)
