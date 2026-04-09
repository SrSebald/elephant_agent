from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.schemas.analysis import AttachmentArtifact, GuardrailFinding, RelevantFile, TicketAnalysis
from app.services.codebase import SolidusCodebaseService
from app.services.communicator import CommunicatorService
from app.services.email import EmailService
from app.services.linear import LinearService
from app.services.llm import LLMService
from app.services.observability import ObservabilityService


class TicketState(TypedDict):
    ticket_id: int
    trace_id: str
    title: str
    reporter_email: str | None
    report_text: str
    file_content: str
    attachments: list[dict]
    guardrail_findings: list[dict]
    analysis: dict | None
    resolution_path: str
    relevant_files: list[dict]
    assigned_team: str
    priority: str
    linear_issue_id: str | None
    linear_issue_url: str | None
    communicator_status: str | None
    communicator_reference: str | None
    status: str
    error_message: str | None


def build_ticket_graph(
    llm_service: LLMService,
    codebase_service: SolidusCodebaseService,
    linear_service: LinearService,
    email_service: EmailService,
    communicator_service: CommunicatorService,
    observability_service: ObservabilityService,
):
    async def analyze_and_inspect(state: TicketState) -> dict:
        attachments = [AttachmentArtifact.model_validate(item) for item in state["attachments"]]
        guardrail_findings = [GuardrailFinding.model_validate(item) for item in state["guardrail_findings"]]

        await observability_service.record(
            ticket_id=state["ticket_id"],
            trace_id=state["trace_id"],
            stage="triage",
            message="Starting Solidus triage.",
            payload={"attachments": len(attachments), "guardrail_findings": len(guardrail_findings)},
        )

        signal = await llm_service.extract_signal(
            report_text=state["report_text"],
            attachments=attachments,
            guardrail_findings=guardrail_findings,
        )
        relevant_files = await codebase_service.search_code(signal.search_queries or signal.keywords)
        analysis = await llm_service.analyze_report(
            title=state["title"],
            report_text=state["report_text"],
            attachments=attachments,
            guardrail_findings=guardrail_findings,
            relevant_files=relevant_files,
        )

        await observability_service.record(
            ticket_id=state["ticket_id"],
            trace_id=state["trace_id"],
            stage="triage",
            message="Solidus triage completed.",
            payload={
                "assigned_team": analysis.assigned_team,
                "priority": analysis.priority,
                "relevant_files": len(relevant_files),
            },
        )

        return {
            "analysis": analysis.model_dump(),
            "resolution_path": analysis.resolution_path,
            "relevant_files": [item.model_dump() for item in relevant_files],
            "assigned_team": analysis.assigned_team,
            "priority": analysis.priority,
            "status": "processing",
        }

    async def execute(state: TicketState) -> dict:
        analysis = TicketAnalysis.model_validate(state["analysis"] or {})
        relevant_files = [RelevantFile.model_validate(item) for item in state["relevant_files"]]

        issue_markdown = _build_linear_issue_body(
            report_text=state["report_text"],
            file_content=state["file_content"],
            analysis=analysis,
            relevant_files=relevant_files,
        )

        try:
            linear_issue = await linear_service.create_issue(
                title=state["title"],
                team_slug=analysis.assigned_team,
                priority=analysis.priority,
                description=issue_markdown,
            )
            await observability_service.record(
                ticket_id=state["ticket_id"],
                trace_id=state["trace_id"],
                stage="ticket",
                message="Ticket created in Linear.",
                payload={
                    "identifier": linear_issue.identifier,
                    "url": linear_issue.url,
                    "team_id": linear_issue.team_id,
                    "team_name": linear_issue.team_name,
                    "dry_run": linear_issue.dry_run,
                },
            )

            team_target = linear_service.get_team_target(analysis.assigned_team)
            email_result = await email_service.send_ticket_notification(
                to_email=team_target.email,
                ticket_title=state["title"],
                analysis=analysis,
                linear_url=linear_issue.url,
            )
            await observability_service.record(
                ticket_id=state["ticket_id"],
                trace_id=state["trace_id"],
                stage="notify",
                message="Email notification dispatched.",
                payload={
                    "team_email": team_target.email,
                    "dry_run": email_result.dry_run,
                    "message_id": email_result.message_id,
                },
            )

            communicator_result = await communicator_service.send_ticket_notification(
                channel=team_target.communicator_channel,
                ticket_title=state["title"],
                summary=analysis.summary,
                linear_url=linear_issue.url,
                trace_id=state["trace_id"],
            )
            await observability_service.record(
                ticket_id=state["ticket_id"],
                trace_id=state["trace_id"],
                stage="communicator",
                message="Communicator notification dispatched.",
                payload={
                    "channel": team_target.communicator_channel,
                    "reference": communicator_result.reference,
                    "dry_run": communicator_result.dry_run,
                },
            )
        except Exception as exc:
            await observability_service.record(
                ticket_id=state["ticket_id"],
                trace_id=state["trace_id"],
                stage="system",
                level="error",
                message="Execution failed.",
                payload={"error": str(exc)},
            )
            return {
                "status": "failed",
                "error_message": str(exc),
            }

        execution_mode = "live"
        if (
            analysis.execution_mode == "dry-run"
            or linear_issue.dry_run
            or email_result.dry_run
            or communicator_result.dry_run
        ):
            execution_mode = "dry-run"

        updated_analysis = analysis.model_copy(update={"execution_mode": execution_mode})

        return {
            "analysis": updated_analysis.model_dump(),
            "linear_issue_id": linear_issue.id,
            "linear_issue_url": linear_issue.url,
            "communicator_status": "mocked" if communicator_result.dry_run else "sent",
            "communicator_reference": communicator_result.reference,
            "status": "routed",
            "error_message": None,
        }

    builder = StateGraph(TicketState)
    builder.add_node(
        "analyze_and_inspect",
        analyze_and_inspect,
        retry_policy=RetryPolicy(max_attempts=2, initial_interval=1.0),
    )
    builder.add_node(
        "execute",
        execute,
        retry_policy=RetryPolicy(max_attempts=2, initial_interval=1.0),
    )
    builder.add_edge(START, "analyze_and_inspect")
    builder.add_edge("analyze_and_inspect", "execute")
    builder.add_edge("execute", END)
    return builder.compile()


def _build_linear_issue_body(
    report_text: str,
    file_content: str,
    analysis: TicketAnalysis,
    relevant_files: list[RelevantFile],
) -> str:
    file_lines = []
    for item in relevant_files:
        line = f"- `{item.repository}/{item.path}`"
        if item.url:
            line += f" ({item.url})"
        file_lines.append(line)

    relevant_files_markdown = "\n".join(file_lines) if file_lines else "- No Solidus code matches were found."
    attachment_excerpt = file_content[:1200].strip() or "No text attachment provided."
    next_steps = "\n".join(f"- {step}" for step in analysis.next_steps) or "- Validate the diagnosis."

    return "\n".join(
        [
            f"# {analysis.summary}",
            "",
            f"**Category:** {analysis.category}",
            f"**Assigned team:** {analysis.assigned_team}",
            f"**Priority:** {analysis.priority}",
            f"**Solidus area:** {analysis.solidus_area}",
            "",
            "## Reporter Context",
            report_text.strip(),
            "",
            "## Diagnosis",
            analysis.diagnosis,
            "",
            "## Resolution Path",
            analysis.resolution_path,
            "",
            "## Suggested Next Steps",
            next_steps,
            "",
            "## Relevant Solidus Files",
            relevant_files_markdown,
            "",
            "## Attachment Excerpt",
            attachment_excerpt,
        ]
    )
