"use client";

import {
  type ChangeEvent,
  type FormEvent,
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useState,
  useTransition,
} from "react";

import type { Ticket, TicketStatus } from "@/lib/types";

type TicketDashboardProps = {
  initialTickets: Ticket[];
};

const STATUS_LABELS: Record<TicketStatus, string> = {
  queued: "Queued",
  processing: "Processing",
  routed: "Routed",
  failed: "Failed",
};

const TEAM_LABELS: Record<string, string> = {
  backend: "Backend",
  frontend: "Frontend",
  infra: "Infra",
};

export function TicketDashboard({ initialTickets }: TicketDashboardProps) {
  const [tickets, setTickets] = useState(initialTickets);
  const deferredTickets = useDeferredValue(tickets);
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(
    initialTickets[0]?.id ?? null,
  );
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isPending, startSubmitTransition] = useTransition();

  const refreshTickets = useEffectEvent(async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch("/api/tickets", { cache: "no-store" });
      const payload = (await response.json()) as Ticket[] | { detail?: string };
      if (!response.ok) {
        throw new Error(
          typeof payload === "object" && payload && "detail" in payload
            ? payload.detail || "Unable to refresh tickets."
            : "Unable to refresh tickets.",
        );
      }

      const nextTickets = payload as Ticket[];
      startTransition(() => {
        setTickets(nextTickets);
        setSelectedTicketId((current) => {
          if (current && nextTickets.some((ticket) => ticket.id === current)) {
            return current;
          }
          return nextTickets[0]?.id ?? null;
        });
      });
      setLastUpdated(new Date().toISOString());
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Unable to refresh tickets."));
    } finally {
      setIsRefreshing(false);
    }
  });

  useEffect(() => {
    void refreshTickets();
    const intervalId = window.setInterval(() => {
      void refreshTickets();
    }, 10_000);
    return () => window.clearInterval(intervalId);
  }, [refreshTickets]);

  const selectedTicket =
    deferredTickets.find((ticket) => ticket.id === selectedTicketId) ?? deferredTickets[0] ?? null;
  const processingCount = deferredTickets.filter((ticket) => ticket.status === "processing").length;
  const routedCount = deferredTickets.filter((ticket) => ticket.status === "routed").length;
  const failedCount = deferredTickets.filter((ticket) => ticket.status === "failed").length;

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setFileNames(Array.from(event.target.files ?? []).map((file) => file.name));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    setFeedbackMessage(null);
    setErrorMessage(null);

    startSubmitTransition(() => {
      void submitTicket(form, formData);
    });
  };

  async function submitTicket(form: HTMLFormElement, formData: FormData) {
    try {
      const response = await fetch("/api/tickets", {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as Ticket | { detail?: string };
      if (!response.ok) {
        throw new Error(
          typeof payload === "object" && payload && "detail" in payload
            ? payload.detail || "Ticket submission failed."
            : "Ticket submission failed.",
        );
      }

      const createdTicket = payload as Ticket;
      form.reset();
      setTitle("");
      setDescription("");
      setFileNames([]);
      setFeedbackMessage(`Ticket #${createdTicket.id} accepted. The agent is already working on it.`);
      setSelectedTicketId(createdTicket.id);
      await refreshTickets();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Ticket submission failed."));
    }
  }

  return (
    <main className="dashboard-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">MVP Ticket Routing</p>
          <h1>Elephant Agent</h1>
          <p className="hero-copy">
            Ingest incidents, inspect code hints, route the ticket, and keep the queue visible while the
            graph runs in the background.
          </p>
        </div>
        <div className="stats-grid">
          <StatCard label="Open Queue" value={String(deferredTickets.length)} accent="sand" />
          <StatCard label="In Flight" value={String(processingCount)} accent="mint" />
          <StatCard label="Routed" value={String(routedCount)} accent="sky" />
          <StatCard label="Needs Attention" value={String(failedCount)} accent="coral" />
        </div>
      </section>

      <section className="panel compose-panel">
        <div className="panel-header">
          <div>
            <p className="panel-kicker">New Report</p>
            <h2>Submit a ticket</h2>
          </div>
          <p className="panel-note">Accepted attachments: .txt, .md, .log</p>
        </div>

        <form className="ticket-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Title</span>
            <input
              name="title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Checkout API returns 500 for promo orders"
              required
            />
          </label>

          <label className="field">
            <span>Description</span>
            <textarea
              name="description"
              rows={6}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe the symptoms, impact, timing, and reproduction clues."
              required
            />
          </label>

          <label className="field">
            <span>Attachment</span>
            <input
              name="files"
              type="file"
              accept=".txt,.md,.log"
              multiple
              onChange={handleFileChange}
            />
          </label>

          <div className="file-strip" aria-live="polite">
            {fileNames.length > 0 ? fileNames.map((file) => <span key={file}>{file}</span>) : <span>No files selected yet.</span>}
          </div>

          <div className="form-actions">
            <button className="submit-button" type="submit" disabled={isPending}>
              {isPending ? "Submitting..." : "Enviar reporte"}
            </button>
            <p className="panel-note">The ticket enters the queue immediately and the dashboard polls every 10 seconds.</p>
          </div>
        </form>

        {feedbackMessage ? <p className="message success">{feedbackMessage}</p> : null}
        {errorMessage ? <p className="message error">{errorMessage}</p> : null}
      </section>

      <section className="workbench">
        <div className="panel queue-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Live Queue</p>
              <h2>Tickets</h2>
            </div>
            <p className="panel-note">
              {isRefreshing ? "Refreshing..." : `Last sync: ${formatSyncTime(lastUpdated)}`}
            </p>
          </div>

          <div className="ticket-table" role="table" aria-label="Ticket queue">
            <div className="ticket-table-head" role="row">
              <span>Title</span>
              <span>Status</span>
              <span>Team</span>
              <span>Priority</span>
              <span>Created</span>
            </div>
            <div className="ticket-table-body">
              {deferredTickets.length === 0 ? (
                <div className="empty-state">
                  <p>No tickets yet.</p>
                  <span>Submit the first incident report to see the queue come alive.</span>
                </div>
              ) : (
                deferredTickets.map((ticket) => (
                  <TicketRow
                    key={ticket.id}
                    ticket={ticket}
                    isSelected={ticket.id === selectedTicket?.id}
                    onSelect={setSelectedTicketId}
                  />
                ))
              )}
            </div>
          </div>
        </div>

        <TicketDetailPanel ticket={selectedTicket} />
      </section>
    </main>
  );
}

type StatCardProps = {
  label: string;
  value: string;
  accent: "sand" | "mint" | "sky" | "coral";
};

function StatCard({ label, value, accent }: StatCardProps) {
  return (
    <article className={`stat-card ${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

type TicketRowProps = {
  ticket: Ticket;
  isSelected: boolean;
  onSelect: (ticketId: number) => void;
};

function TicketRow({ ticket, isSelected, onSelect }: TicketRowProps) {
  return (
    <button
      className={`ticket-row ${isSelected ? "selected" : ""}`}
      type="button"
      onClick={() => onSelect(ticket.id)}
    >
      <span className="ticket-title-cell">
        <strong>{ticket.title}</strong>
        <small>#{ticket.id}</small>
      </span>
      <span>
        <StatusBadge status={ticket.status} />
      </span>
      <span>{TEAM_LABELS[ticket.assigned_team ?? ticket.analysis?.assigned_team ?? ""] ?? "Pending"}</span>
      <span>{formatPriority(ticket.priority ?? ticket.analysis?.priority ?? "medium")}</span>
      <span>{formatDate(ticket.created_at)}</span>
    </button>
  );
}

function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`status-badge ${status}`}>{STATUS_LABELS[status]}</span>;
}

function TicketDetailPanel({ ticket }: { ticket: Ticket | null }) {
  if (!ticket) {
    return (
      <aside className="panel detail-panel">
        <div className="panel-header">
          <div>
            <p className="panel-kicker">Inspection</p>
            <h2>Ticket detail</h2>
          </div>
        </div>
        <div className="empty-state detail-empty">
          <p>Select a ticket from the queue.</p>
          <span>The full analysis, file matches, and Linear link will appear here.</span>
        </div>
      </aside>
    );
  }

  const analysis = ticket.analysis;

  return (
    <aside className="panel detail-panel">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Inspection</p>
          <h2>{ticket.title}</h2>
        </div>
        <StatusBadge status={ticket.status} />
      </div>

      <div className="detail-grid">
        <article className="detail-card">
          <p className="detail-label">Reporter Context</p>
          <p className="detail-copy">{ticket.description}</p>
        </article>

        <article className="detail-card">
          <p className="detail-label">Routing</p>
          <p className="detail-copy">
            {TEAM_LABELS[ticket.assigned_team ?? analysis?.assigned_team ?? ""] ?? "Pending"} /{" "}
            {formatPriority(ticket.priority ?? analysis?.priority ?? "medium")}
          </p>
          <p className="detail-meta">
            {analysis
              ? `${analysis.category.toUpperCase()} / confidence ${Math.round(analysis.confidence * 100)}%`
              : "Waiting for analysis"}
          </p>
        </article>

        <article className="detail-card emphasis">
          <p className="detail-label">Diagnosis</p>
          <p className="detail-copy">{analysis?.diagnosis ?? "The graph has not produced a diagnosis yet."}</p>
        </article>

        <article className="detail-card">
          <p className="detail-label">Resolution Path</p>
          <p className="detail-copy">{analysis?.resolution_path ?? "Pending."}</p>
        </article>

        <article className="detail-card">
          <p className="detail-label">Keywords</p>
          <div className="token-strip">
            {analysis?.keywords?.length ? analysis.keywords.map((keyword) => <span key={keyword}>{keyword}</span>) : <span>Awaiting extraction.</span>}
          </div>
        </article>

        <article className="detail-card">
          <p className="detail-label">Execution Mode</p>
          <p className="detail-copy">
            {analysis?.execution_mode === "dry-run"
              ? "Dry-run fallback because one or more external integrations are missing."
              : "Live integrations active."}
          </p>
        </article>
      </div>

      <article className="detail-section">
        <div className="section-title">
          <h3>Relevant files</h3>
          <span>{ticket.relevant_files.length} matches</span>
        </div>
        {ticket.relevant_files.length ? (
          <div className="relevant-list">
            {ticket.relevant_files.map((file) => (
              <a
                key={`${file.repository}-${file.path}`}
                className="relevant-file"
                href={file.url ?? "#"}
                target="_blank"
                rel="noreferrer"
              >
                <strong>{file.path}</strong>
                <span>{file.repository}</span>
                <small>{file.snippet || "Snippet unavailable."}</small>
              </a>
            ))}
          </div>
        ) : (
          <div className="empty-inline">No GitHub matches stored for this ticket yet.</div>
        )}
      </article>

      <article className="detail-section">
        <div className="section-title">
          <h3>Next steps</h3>
          <span>{analysis?.next_steps.length ?? 0} suggested actions</span>
        </div>
        {analysis?.next_steps.length ? (
          <div className="steps-list">
            {analysis.next_steps.map((step) => (
              <p key={step}>{step}</p>
            ))}
          </div>
        ) : (
          <div className="empty-inline">Suggested actions will appear once the analysis finishes.</div>
        )}
      </article>

      <article className="detail-section">
        <div className="section-title">
          <h3>Delivery</h3>
          <span>{ticket.linear_issue_id ?? "No Linear issue id yet"}</span>
        </div>
        <div className="delivery-row">
          <p className="detail-copy">
            {ticket.linear_issue_url ? (
              <a href={ticket.linear_issue_url} target="_blank" rel="noreferrer">
                Open Linear issue
              </a>
            ) : (
              "Linear link unavailable in dry-run mode or before execution."
            )}
          </p>
          {ticket.error_message ? <p className="message error inline">{ticket.error_message}</p> : null}
        </div>
      </article>
    </aside>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatSyncTime(value: string | null) {
  if (!value) {
    return "awaiting first sync";
  }

  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatPriority(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}
