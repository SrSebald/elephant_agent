# SCALING

## Current Assumptions

This project is optimized for evaluation, demos, and small-team incident routing rather than high-throughput production traffic.

Assumptions:

- low to moderate daily ticket volume
- bounded attachment sizes
- a single fixed target repository
- operator-driven resolution rather than full automation
- mock-capable integrations are acceptable when secrets are absent

## Current Scaling Characteristics

### Backend

- FastAPI is async and keeps request handlers lightweight.
- Ticket processing is offloaded to background tasks after ingestion.
- LangGraph execution is short-lived and single-ticket scoped.
- SQLite keeps the demo simple and portable.

### Frontend

- Next.js serves a single operator dashboard.
- Initial server rendering loads current queue state.
- Client polling refreshes tickets and observability summary every 10 seconds.
- Event details are fetched only for the selected ticket.

### Codebase Search

- The Solidus repository is cloned once into a persistent Docker volume.
- Search is bounded to a small number of top matches.
- Searchable suffixes and skipped directories reduce scan cost.

## Bottlenecks

The likely first constraints are:

- SQLite write contention under concurrent ticket ingestion
- local repository scan cost as ticket volume grows
- external LLM latency
- background task execution being tied to the API process
- polling overhead if many dashboards are open simultaneously

## What We Would Change For Production

1. Replace SQLite with PostgreSQL.
2. Move background execution to a queue such as Celery, Dramatiq, or a durable workflow runtime.
3. Replace directory walking with a code index:
   - ripgrep-backed search
   - repository embeddings
   - precomputed ownership maps for Solidus
4. Add retries, circuit breakers, and idempotency keys around external integrations.
5. Export metrics to Prometheus and traces to OpenTelemetry.
6. Replace polling with SSE or WebSockets for ticket/event updates.
7. Split the communicator, notification, and triage workers if throughput justifies it.

## Technical Decisions

### Why SQLite now

- zero host dependency
- simple Docker story
- fast enough for demo traffic
- easy to inspect during review

### Why a fixed Solidus target

- evaluation requires a real medium/complex e-commerce codebase
- fixed ownership and prompts are more trustworthy than generic repository guessing
- demo traces become easier to explain and verify

### Why dry-run adapters

- the application must remain demoable without vendor credentials
- reviewers can still see downstream effects in the event log and UI
- switching to live mode is controlled through environment variables only

## Horizontal Scaling Path

The cleanest scale-out path is:

1. stateless FastAPI containers behind a load balancer
2. shared PostgreSQL for tickets and events
3. shared object storage for attachment blobs if artifact size increases
4. dedicated worker pool for triage/execution/resolution notifications
5. centralized tracing and metrics backend

At that point the current API surface can stay mostly stable while the internals move from single-process demo behavior to queue-backed distributed execution.
