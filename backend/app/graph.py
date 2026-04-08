from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.schemas.analysis import RelevantFile, TicketAnalysis
from app.services.email import EmailService
from app.services.github import GitHubService
from app.services.linear import LinearService
from app.services.llm import LLMService


class TicketState(TypedDict):
    ticket_id: int
    title: str
    report_text: str
    file_content: str
    analysis: dict | None
    resolution_path: str
    relevant_files: list[dict]
    assigned_team: str
    priority: str
    linear_issue_id: str | None
    linear_issue_url: str | None
    email_sent: bool
    status: str
    error_message: str | None


def build_ticket_graph(
    llm_service: LLMService,
    github_service: GitHubService,
    linear_service: LinearService,
    email_service: EmailService,
):
    async def analyze_and_inspect(state: TicketState) -> dict:
        signal = await llm_service.extract_signal(
            report_text=state["report_text"],
            file_content=state["file_content"],
        )
        relevant_files = await github_service.search_code(signal.search_queries or signal.keywords)
        analysis = await llm_service.analyze_report(
            title=state["title"],
            report_text=state["report_text"],
            file_content=state["file_content"],
            relevant_files=relevant_files,
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
            team_target = linear_service.get_team_target(analysis.assigned_team)
            email_result = await email_service.send_ticket_notification(
                to_email=team_target.email,
                ticket_title=state["title"],
                analysis=analysis,
                linear_url=linear_issue.url,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "error_message": str(exc),
            }

        execution_mode = "live"
        if analysis.execution_mode == "dry-run" or linear_issue.dry_run or email_result.dry_run:
            execution_mode = "dry-run"

        updated_analysis = analysis.model_copy(update={"execution_mode": execution_mode})

        return {
            "analysis": updated_analysis.model_dump(),
            "linear_issue_id": linear_issue.id,
            "linear_issue_url": linear_issue.url,
            "email_sent": email_result.sent,
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

    relevant_files_markdown = "\n".join(file_lines) if file_lines else "- No GitHub matches were found."
    attachment_excerpt = file_content[:1200].strip() or "No attachment content provided."
    next_steps = "\n".join(f"- {step}" for step in analysis.next_steps) or "- Validate the diagnosis."

    return "\n".join(
        [
            f"# {analysis.summary}",
            "",
            f"**Category:** {analysis.category}",
            f"**Assigned team:** {analysis.assigned_team}",
            f"**Priority:** {analysis.priority}",
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
            "## Relevant Files",
            relevant_files_markdown,
            "",
            "## Attachment Excerpt",
            attachment_excerpt,
        ]
    )
