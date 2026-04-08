# Elephant Agent

MVP end-to-end for incident intake and routing:

- `frontend/`: Next.js dashboard with a report form, ticket queue, polling, and expandable ticket detail.
- `backend/`: FastAPI API with SQLite storage, a two-node LangGraph workflow, GitHub inspection, Linear issue creation, and Resend notification hooks.

## What the MVP does

1. Accepts a title, description, and `.txt` / `.md` / `.log` attachments.
2. Creates a queued ticket in SQLite.
3. Runs a LangGraph workflow in the background:
   - `analyze_and_inspect`
   - `execute`
4. Updates the dashboard by polling every 10 seconds.

## Structure

```text
backend/
  app/
    api/
    core/
    repositories/
    schemas/
    services/
    graph.py
    main.py
frontend/
  app/
  components/
  lib/
```

## Backend setup

```bash
cd backend
pip install -e .
copy .env.example .env
uvicorn app.main:app --reload
```

Important environment variables:

- `OPENAI_API_KEY`
- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPOSITORIES`
- `LINEAR_API_KEY`
- `LINEAR_BACKEND_TEAM_ID`
- `LINEAR_FRONTEND_TEAM_ID`
- `LINEAR_INFRA_TEAM_ID`
- `RESEND_API_KEY`

If those integrations are missing, the backend falls back to `dry-run` mode so the full queue and routing flow can still be demoed.

## Frontend setup

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`

## API

- `GET /api/v1/tickets`
- `POST /api/v1/tickets`
- `GET /health`
