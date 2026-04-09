# Elephant Agent

Elephant Agent is a multimodal support triage system for the Solidus e-commerce codebase. It accepts incident text plus image or log evidence, applies prompt-injection guardrails, routes the report to the right Solidus team, emits demoable downstream integrations, and records observable stage-by-stage traces from ingest through resolution.

## What It Covers

- Multimodal intake: text, `.txt`, `.md`, `.log`, `.png`, `.jpg`, `.jpeg`, `.webp`
- Multimodal LLM support through an OpenAI-compatible chat-completions API
- Guardrails for attachment size, MIME/extension filtering, binary detection, and prompt-injection pattern detection
- Observability with structured logs, persisted ticket events, trace IDs, stage counters, and queue metrics
- Demoable integrations for ticketing, email, and communicator channels in either live or mocked mode
- Fixed e-commerce target repository: `solidusio/solidus`

## Architecture

The application runs as two services behind Docker Compose:

- `frontend/`: Next.js dashboard for submission, observability, event review, and manual resolution
- `backend/`: FastAPI API, SQLite persistence, LangGraph workflow, and integration adapters

Main flow:

1. User submits a ticket with text and optional artifacts.
2. FastAPI stores the ticket, attachments metadata, and an `ingest` event.
3. A LangGraph workflow executes `analyze_and_inspect -> execute`.
4. The backend searches the Solidus repository and produces a Solidus-specific triage analysis.
5. Ticketing, email, and communicator notifications are sent live or mocked.
6. The UI polls tickets, metrics, and per-ticket event traces.
7. A reviewer can mark the ticket as resolved, which emits `resolved` notifications and events.

## Core Components

- [backend/app/services/ingestion.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/ingestion.py): multimodal ingestion and guardrails
- [backend/app/services/llm.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/llm.py): OpenAI-compatible multimodal analysis for Solidus routing
- [backend/app/services/codebase.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/codebase.py): fixed Solidus repo clone/search service
- [backend/app/graph.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/graph.py): LangGraph orchestration
- [backend/app/services/observability.py](C:/Users/werne/Documents/GitHub/elephant_agent/backend/app/services/observability.py): logs, persisted traces, and metrics summary
- [frontend/components/ticket-dashboard.tsx](C:/Users/werne/Documents/GitHub/elephant_agent/frontend/components/ticket-dashboard.tsx): dashboard with queue, stage metrics, events, and resolve action

## Repository Layout

```text
backend/
  app/
  Dockerfile
frontend/
  app/
  components/
  lib/
  Dockerfile
scripts/
AGENTS_USE.md
SCALING.md
QUICKGUIDE.md
docker-compose.yml
.env.example
```

## Run With Docker

1. Copy `.env.example` to `.env`.
2. Fill in keys if you want live integrations. Leaving them empty keeps the app demoable in mock mode.
3. Start the stack:

```bash
docker compose up --build
```

Open `http://localhost:3000`.

The frontend is the only published port. The backend stays internal on the Docker network and is reached by the frontend at `http://backend:8000`.

## Environment Notes

- For OpenAI: set `OPENAI_API_KEY`, keep `OPENAI_BASE_URL=https://api.openai.com/v1`
- For OpenRouter: set `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and use an OpenRouter model name in `OPENAI_MODEL`
- For Solidus code search: leave `SOLIDUS_AUTO_CLONE=true` to clone `solidusio/solidus` into the Docker volume on startup
- For mocked operation: keep `ALLOW_DRY_RUN=true` and leave integration keys empty

## Demo Surface

- Submit a report with `scripts/sample-solidus.log` plus `scripts/pixel.png`
- Watch the queue move from `queued` to `routed`
- Inspect `ingest`, `guardrails`, `triage`, `ticket`, `notify`, `communicator`, and `resolved` events in the UI
- Mark the ticket as resolved from the dashboard

## Additional Docs

- [AGENTS_USE.md](C:/Users/werne/Documents/GitHub/elephant_agent/AGENTS_USE.md)
- [SCALING.md](C:/Users/werne/Documents/GitHub/elephant_agent/SCALING.md)
- [QUICKGUIDE.md](C:/Users/werne/Documents/GitHub/elephant_agent/QUICKGUIDE.md)
