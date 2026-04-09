# AGENTS_USE

## Use Cases

- Support teams ingest a Solidus production incident with text plus image or log evidence.
- The agent triages the report against the Solidus codebase and assigns it to `core`, `admin`, or `api`.
- The system creates a ticket, emits email and communicator notifications, and preserves an observable trace.
- A human operator can manually resolve the ticket and emit a final `resolved` stage.

## Agent Workflow

The backend workflow is implemented in [backend/app/graph.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/graph.py) with LangGraph:

1. `analyze_and_inspect`
2. `execute`

`analyze_and_inspect`:

- reads the stored ticket state
- converts attachments into trusted metadata plus untrusted evidence
- runs keyword extraction and multimodal analysis through [backend/app/services/llm.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/llm.py)
- searches the fixed Solidus repository via [backend/app/services/codebase.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/codebase.py)
- records `triage` events

`execute`:

- creates a Linear issue or a dry-run ticket via [backend/app/services/linear.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/linear.py)
- sends email or mock email via [backend/app/services/email.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/email.py)
- sends communicator webhook or mock communicator delivery via [backend/app/services/communicator.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/communicator.py)
- records `ticket`, `notify`, and `communicator` events

Manual resolution is handled in [backend/app/services/ticket_service.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/ticket_service.py) and records the `resolved` stage.

## Solidus-Specific Adaptation

The project is fixed to `solidusio/solidus`, a medium-to-large Ruby on Rails e-commerce platform.

- The repo target is configured in `.env` through `SOLIDUS_REPO_URL`, `SOLIDUS_REPO_BRANCH`, and `SOLIDUS_LOCAL_PATH`.
- Search results are turned into relevant file links back to GitHub.
- Routing is specialized to Solidus ownership surfaces:
  - `core`: orders, checkout, payments, shipments, promotions, inventory
  - `admin`: backend/admin surfaces
  - `api`: API endpoints and serializers
- The analysis prompt references `solidus_core`, `solidus_backend`, `solidus_api`, and `solidus_sample`.

## Multimodal Input

Supported inputs are enforced in [backend/app/services/ingestion.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/ingestion.py):

- text report body
- `.txt`, `.md`, `.log`
- `.png`, `.jpg`, `.jpeg`, `.webp`

Text attachments are decoded, size-limited, scanned, and excerpted. Images are encoded into `data:` URLs so the OpenAI-compatible API receives true multimodal content.

## Safety Measures

Guardrails are intentionally simple but demoable:

- per-file and total upload byte limits
- attachment count limits
- extension and MIME-type gating
- UTF-8 and printable-text validation for text artifacts
- prompt-injection pattern scanning for phrases such as `ignore previous`, `system prompt`, `developer message`, `tool call`, `api key`, and destructive shell strings
- explicit LLM instructions to treat artifacts as untrusted evidence and never follow attachment instructions
- dry-run tool adapters so no live external side effect is required for a demo

Guardrail findings are stored with the ticket and also emitted as `guardrails` events.

## Observability Evidence

The main observable path is:

`ingest -> guardrails -> triage -> ticket -> notify -> communicator -> resolved`

Evidence sources:

- Structured backend logs from [backend/app/services/observability.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/observability.py)
- Persisted trace rows in the `ticket_events` table via [backend/app/repositories/event_repository.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/repositories/event_repository.py)
- Summary metrics at `GET /api/v1/tickets/observability/summary`
- Per-ticket traces at `GET /api/v1/tickets/{ticket_id}/events`
- UI display in [frontend/components/ticket-dashboard.tsx](C:/Users/werne/Documents/GitHub/elephant_agent/frontend/components/ticket-dashboard.tsx)

Observable fields include:

- `trace_id`
- `stage`
- `level`
- event payloads
- queue status counts
- stage counts
- latest event timestamp

## Demoable Integrations

- Ticketing: Linear API or dry-run issue references
- Email: Resend API or dry-run notification receipts
- Communicator: webhook-based channel delivery or mock references

The UI makes the mocks visible through:

- the delivery section on each ticket
- the event trace panel
- the stage metrics strip

## Relevant Endpoints

- `GET /health`
- `GET /api/v1/tickets`
- `POST /api/v1/tickets`
- `GET /api/v1/tickets/observability/summary`
- `GET /api/v1/tickets/{ticket_id}/events`
- `POST /api/v1/tickets/{ticket_id}/resolve`
