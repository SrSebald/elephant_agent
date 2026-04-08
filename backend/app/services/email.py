from dataclasses import dataclass
from html import escape

import httpx

from app.core.config import Settings
from app.schemas.analysis import TicketAnalysis


@dataclass(slots=True)
class EmailResult:
    sent: bool
    message_id: str | None = None
    dry_run: bool = False


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_ticket_notification(
        self,
        *,
        to_email: str,
        ticket_title: str,
        analysis: TicketAnalysis,
        linear_url: str | None,
    ) -> EmailResult:
        if not self.settings.resend_api_key or not to_email:
            if self.settings.allow_dry_run:
                return EmailResult(sent=True, dry_run=True)
            raise RuntimeError("Resend is not configured. Set RESEND_API_KEY and target emails.")

        payload = {
            "from": self.settings.resend_from_email,
            "to": [to_email],
            "subject": f"New ticket routed: {ticket_title}",
            "html": self._build_html(ticket_title=ticket_title, analysis=analysis, linear_url=linear_url),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

        return EmailResult(sent=True, message_id=response.json().get("id"))

    def _build_html(self, *, ticket_title: str, analysis: TicketAnalysis, linear_url: str | None) -> str:
        next_steps = "".join(f"<li>{escape(step)}</li>" for step in analysis.next_steps) or "<li>Validate the diagnosis.</li>"
        link = (
            f'<p><a href="{escape(linear_url)}">Open Linear issue</a></p>'
            if linear_url
            else "<p>Linear issue URL unavailable in dry-run mode.</p>"
        )
        return f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #111827;">
          <h2>{escape(ticket_title)}</h2>
          <p><strong>Team:</strong> {escape(analysis.assigned_team.title())}</p>
          <p><strong>Priority:</strong> {escape(analysis.priority.title())}</p>
          <p><strong>Diagnosis:</strong> {escape(analysis.diagnosis)}</p>
          <h3>Resolution Path</h3>
          <p>{escape(analysis.resolution_path)}</p>
          <h3>Next Steps</h3>
          <ul>{next_steps}</ul>
          {link}
        </div>
        """
