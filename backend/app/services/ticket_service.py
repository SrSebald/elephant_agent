from uuid import uuid4

import aiosqlite
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.database import connection_context
from app.graph import build_ticket_graph
from app.repositories.ticket_repository import TicketRepository, ticket_repository
from app.schemas.analysis import AttachmentArtifact, TicketAnalysis
from app.schemas.context import AppContext, EcommerceContext, LinearContext, LinearTeamTarget
from app.schemas.events import ObservabilitySummary, TicketEvent
from app.schemas.tickets import TicketRecord
from app.services.codebase import SolidusCodebaseService
from app.services.communicator import CommunicatorService
from app.services.email import EmailService
from app.services.ingestion import IngestionService
from app.services.linear import LinearService
from app.services.llm import LLMService
from app.services.observability import ObservabilityService, observability_service


class TicketService:
    def __init__(self, repository: TicketRepository, observability: ObservabilityService):
        self.repository = repository
        self.observability = observability
        self.settings = get_settings()
        self.ingestion_service = IngestionService(self.settings)
        self.llm_service = LLMService(self.settings)
        self.codebase_service = SolidusCodebaseService(self.settings)
        self.linear_service = LinearService(self.settings)
        self.email_service = EmailService(self.settings)
        self.communicator_service = CommunicatorService(self.settings)
        self.workflow = build_ticket_graph(
            llm_service=self.llm_service,
            codebase_service=self.codebase_service,
            linear_service=self.linear_service,
            email_service=self.email_service,
            communicator_service=self.communicator_service,
            observability_service=self.observability,
        )

    async def list_tickets(self, connection: aiosqlite.Connection) -> list[TicketRecord]:
        return await self.repository.list_tickets(connection)

    async def get_ticket(self, connection: aiosqlite.Connection, ticket_id: int) -> TicketRecord | None:
        return await self.repository.get_ticket(connection, ticket_id)

    async def list_events(self, ticket_id: int) -> list[TicketEvent]:
        return await self.observability.list_ticket_events(ticket_id)

    async def observability_summary(self) -> ObservabilitySummary:
        return await self.observability.summary()

    def app_context(self) -> AppContext:
        linear_targets: list[LinearTeamTarget] = []
        for team in self.linear_service.team_catalog.values():
            _, effective_team_id, effective_team_name = self.linear_service.resolve_team_destination(team.slug)
            linear_targets.append(
                LinearTeamTarget(
                    slug=team.slug,
                    display_name=team.display_name,
                    configured_team_id=team.linear_team_id,
                    effective_team_id=effective_team_id,
                    effective_team_name=effective_team_name,
                )
            )

        linear_ready = bool(self.settings.linear_api_key and any(item.effective_team_id for item in linear_targets))
        return AppContext(
            ecommerce=EcommerceContext(
                name=self.settings.ecommerce_name,
                platform=self.settings.ecommerce_platform,
                storefront_url=self.settings.ecommerce_storefront_url,
                admin_url=self.settings.ecommerce_admin_url,
                support_email=self.settings.ecommerce_support_email,
                codebase_repo_url=self.settings.solidus_repo_url,
                codebase_branch=self.settings.solidus_repo_branch,
            ),
            linear=LinearContext(
                connected=linear_ready,
                mode="live" if linear_ready else "dry-run",
                default_team_id=self.settings.linear_default_team_id,
                default_team_name=self.settings.linear_default_team_name,
                targets=linear_targets,
            ),
        )

    async def create_ticket_submission(
        self,
        *,
        connection: aiosqlite.Connection,
        title: str,
        reporter_email: str | None,
        description: str,
        files: list[UploadFile],
    ) -> TicketRecord:
        clean_title = title.strip()
        clean_description = description.strip()
        clean_reporter_email = reporter_email.strip() if reporter_email else None
        if not clean_title:
            raise ValueError("Title cannot be empty.")
        if not clean_description:
            raise ValueError("Description cannot be empty.")

        trace_id = uuid4().hex[:12]
        ingestion_result = await self.ingestion_service.ingest_files(files)
        ticket = await self.repository.create_ticket(
            connection,
            title=clean_title,
            reporter_email=clean_reporter_email,
            description=clean_description,
            file_content=ingestion_result.file_content,
            trace_id=trace_id,
            attachments=[item.persisted_dict() for item in ingestion_result.attachments],
            guardrail_findings=[item.model_dump() for item in ingestion_result.guardrail_findings],
        )

        await self.observability.record(
            ticket_id=ticket.id,
            trace_id=ticket.trace_id,
            stage="ingest",
            message="Ticket accepted.",
            payload={
                "reporter_email": ticket.reporter_email,
                "attachments": [item.filename for item in ingestion_result.attachments],
            },
        )

        if ingestion_result.guardrail_findings:
            await self.observability.record(
                ticket_id=ticket.id,
                trace_id=ticket.trace_id,
                stage="guardrails",
                level="warning",
                message="Guardrail findings detected in attachments.",
                payload={"findings": [item.model_dump() for item in ingestion_result.guardrail_findings]},
            )

        return ticket

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
                {"configurable": {"thread_id": ticket.trace_id}},
            )
        except Exception as exc:
            await self.observability.record(
                ticket_id=ticket.id,
                trace_id=ticket.trace_id,
                stage="system",
                level="error",
                message="Workflow execution failed.",
                payload={"error": str(exc)},
            )
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
                communicator_status=result.get("communicator_status"),
                communicator_reference=result.get("communicator_reference"),
                assigned_team=result.get("assigned_team"),
                priority=result.get("priority"),
                error_message=result.get("error_message"),
            )

    async def resolve_ticket(self, ticket_id: int, resolution_note: str) -> TicketRecord:
        async with connection_context() as connection:
            ticket = await self.repository.get_ticket(connection, ticket_id)
            if ticket is None:
                raise ValueError("Ticket not found.")

        note = resolution_note.strip() or "Resolved manually from the dashboard."
        team_slug = ticket.assigned_team if ticket.assigned_team in {"core", "admin", "api"} else "core"
        priority = ticket.priority if ticket.priority in {"low", "medium", "high", "critical"} else "medium"
        analysis = ticket.analysis or TicketAnalysis(
            category="bug",
            summary=ticket.title,
            diagnosis="Resolved manually.",
            resolution_path=note,
            assigned_team=team_slug,
            priority=priority,
            solidus_area="solidus_core",
            execution_mode="dry-run",
        )
        team_target = self.linear_service.get_team_target(analysis.assigned_team)

        reporter_result = await self.email_service.send_resolution_notification(
            to_email=ticket.reporter_email or team_target.email,
            ticket_title=ticket.title,
            resolution_note=note,
        )
        communicator_result = await self.communicator_service.send_resolution_notification(
            channel=team_target.communicator_channel,
            ticket_title=ticket.title,
            resolution_note=note,
            trace_id=ticket.trace_id,
        )

        await self.observability.record(
            ticket_id=ticket.id,
            trace_id=ticket.trace_id,
            stage="resolved",
            message="Ticket resolved.",
            payload={
                "resolution_note": note,
                "email_dry_run": reporter_result.dry_run,
                "communicator_dry_run": communicator_result.dry_run,
            },
        )

        async with connection_context() as connection:
            updated = await self.repository.update_ticket(
                connection,
                ticket_id,
                status="resolved",
                resolution_note=note,
                resolved_at=self.repository._utc_now(),
            )

        if updated is None:
            raise ValueError("Ticket not found after update.")
        return updated

    async def warm_codebase(self) -> None:
        try:
            await self.codebase_service.ensure_repo()
        except Exception:
            return

    @staticmethod
    def _build_state(ticket: TicketRecord) -> dict:
        return {
            "ticket_id": ticket.id,
            "trace_id": ticket.trace_id,
            "title": ticket.title,
            "reporter_email": ticket.reporter_email,
            "report_text": f"{ticket.title}\n\n{ticket.description}",
            "file_content": ticket.file_content,
            "attachments": [item.model_dump() for item in ticket.attachments],
            "guardrail_findings": [item.model_dump() for item in ticket.guardrail_findings],
            "analysis": ticket.analysis.model_dump() if ticket.analysis else None,
            "resolution_path": ticket.resolution_path or "",
            "relevant_files": [item.model_dump() for item in ticket.relevant_files],
            "assigned_team": ticket.assigned_team or "core",
            "priority": ticket.priority or "medium",
            "linear_issue_id": ticket.linear_issue_id,
            "linear_issue_url": ticket.linear_issue_url,
            "communicator_status": ticket.communicator_status,
            "communicator_reference": ticket.communicator_reference,
            "status": ticket.status,
            "error_message": ticket.error_message,
        }


ticket_service = TicketService(ticket_repository, observability_service)
