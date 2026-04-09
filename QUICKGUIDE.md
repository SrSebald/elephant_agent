# QUICKGUIDE

## Run In Minutes

1. Clone the repository.
2. Copy `.env.example` to `.env`.
3. Fill in keys if you want live integrations.
4. Start everything:

```bash
docker compose up --build
```

5. Open `http://localhost:3000`.

## Minimal Demo Mode

If you just want a working demo, leave these blank:

- `OPENAI_API_KEY`
- `LINEAR_API_KEY`
- `RESEND_API_KEY`
- `COMMUNICATOR_WEBHOOK_URL`

Keep this enabled:

```env
ALLOW_DRY_RUN=true
SOLIDUS_AUTO_CLONE=true
```

The app will still accept reports, route them with fallback heuristics, create mock downstream events, and let you resolve tickets from the UI.

## OpenRouter Support

Use these settings in `.env`:

```env
OPENAI_API_KEY=your_openrouter_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4.1-mini
OPENAI_SITE_URL=http://localhost:3000
OPENAI_APP_NAME=Elephant Agent
```

Any OpenAI-compatible multimodal model name can be used here.

## Suggested Demo Steps

1. Open the dashboard.
2. Submit a ticket with:
   - title describing a Solidus checkout/admin/API problem
   - description with reproduction details
   - `scripts/sample-solidus.log`
   - `scripts/pixel.png`
3. Watch the queue move from `queued` to `routed`.
4. Open the ticket detail panel and review:
   - guardrail findings
   - relevant Solidus files
   - event trace
   - mocked or live delivery status
5. Mark the ticket as resolved and confirm the `resolved` event appears.

## Ports

- `3000`: Next.js frontend

The backend runs only inside Docker Compose and is not exposed publicly.

## Troubleshooting

- If the first start takes a while, the backend may be cloning `solidusio/solidus` into the Docker volume.
- If you want live Solidus-aware multimodal routing, provide a valid OpenAI-compatible API key.
- If you change environment variables, restart with `docker compose up --build`.
