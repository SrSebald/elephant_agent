from dataclasses import dataclass

import httpx

from app.core.config import Settings


@dataclass(slots=True)
class CommunicatorResult:
    sent: bool
    reference: str | None = None
    dry_run: bool = False


class CommunicatorService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_ticket_notification(
        self,
        *,
        channel: str,
        ticket_title: str,
        summary: str,
        linear_url: str | None,
        trace_id: str,
    ) -> CommunicatorResult:
        if not self.settings.communicator_webhook_url:
            return CommunicatorResult(
                sent=True,
                reference=f"mock://communicator/{trace_id}",
                dry_run=True,
            )

        text = f"[{trace_id}] {ticket_title}\n{summary}"
        if linear_url:
            text += f"\nLinear: {linear_url}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self.settings.communicator_webhook_url,
                json={
                    "text": text,
                    "channel": channel,
                },
            )
            response.raise_for_status()

        return CommunicatorResult(sent=True, reference=channel)

    async def send_resolution_notification(
        self,
        *,
        channel: str,
        ticket_title: str,
        resolution_note: str,
        trace_id: str,
    ) -> CommunicatorResult:
        if not self.settings.communicator_webhook_url:
            return CommunicatorResult(
                sent=True,
                reference=f"mock://communicator/resolved/{trace_id}",
                dry_run=True,
            )

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self.settings.communicator_webhook_url,
                json={
                    "text": f"[{trace_id}] Resolved: {ticket_title}\n{resolution_note}",
                    "channel": channel,
                },
            )
            response.raise_for_status()

        return CommunicatorResult(sent=True, reference=channel)
