"use client";

import {
  type ChangeEvent,
  type FormEvent,
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";

import type { AppContext, ObservabilitySummary, Ticket, TicketEvent, TicketStatus } from "@/lib/types";

type TicketDashboardProps = {
  initialTickets: Ticket[];
  initialSummary: ObservabilitySummary | null;
  initialContext: AppContext | null;
};

const STATUS_LABELS: Record<TicketStatus, string> = {
  queued: "Queued",
  processing: "Processing",
  routed: "Routed",
  resolved: "Resolved",
  failed: "Failed",
};

const TEAM_LABELS: Record<string, string> = {
  core: "Solidus Core",
  admin: "Solidus Admin",
  api: "Solidus API",
};

const STAGE_LABELS: Record<string, string> = {
  ingest: "Ingest",
  guardrails: "Guardrails",
  triage: "Triage",
  ticket: "Ticket",
  notify: "Notify",
  communicator: "Communicator",
  resolved: "Resolved",
  system: "System",
};

export function TicketDashboard({ initialTickets, initialSummary, initialContext }: TicketDashboardProps) {
  const [tickets, setTickets] = useState(initialTickets);
  const [summary, setSummary] = useState<ObservabilitySummary | null>(initialSummary);
  const [context, setContext] = useState<AppContext | null>(initialContext);
  const deferredTickets = useDeferredValue(tickets);
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(initialTickets[0]?.id ?? null);
  const [selectedEvents, setSelectedEvents] = useState<TicketEvent[]>([]);
  const [reporterEmail, setReporterEmail] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [resolutionNote, setResolutionNote] = useState("Resolved manually from the dashboard.");
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isEventsRefreshing, setIsEventsRefreshing] = useState(false);
  const [isPending, startSubmitTransition] = useTransition();
  const [isResolving, startResolveTransition] = useTransition();
  const isActiveRef = useRef(true);

  const selectedTicket =
    deferredTickets.find((ticket) => ticket.id === selectedTicketId) ?? deferredTickets[0] ?? null;

  useEffect(() => {
    isActiveRef.current = true;
    return () => {
      isActiveRef.current = false;
    };
  }, []);

  async function refreshDashboard() {
    setIsRefreshing(true);
    try {
      const [ticketsResponse, summaryResponse] = await Promise.all([
        fetch("/api/tickets", { cache: "no-store" }),
        fetch("/api/observability/summary", { cache: "no-store" }),
      ]);
      const ticketsPayload = (await ticketsResponse.json()) as Ticket[] | { detail?: string };
      const summaryPayload = (await summaryResponse.json()) as ObservabilitySummary | { detail?: string };

      if (!ticketsResponse.ok) {
        throw new Error(readDetail(ticketsPayload, "Unable to refresh tickets."));
      }
      if (!summaryResponse.ok) {
        throw new Error(readDetail(summaryPayload, "Unable to refresh observability summary."));
      }

      const nextTickets = ticketsPayload as Ticket[];
      const nextSummary = summaryPayload as ObservabilitySummary;
      if (!isActiveRef.current) {
        return;
      }

      startTransition(() => {
        setTickets(nextTickets);
        setSummary(nextSummary);
        setSelectedTicketId((current) => {
          if (current && nextTickets.some((ticket) => ticket.id === current)) {
            return current;
          }
          return nextTickets[0]?.id ?? null;
        });
      });
      setLastUpdated(new Date().toISOString());
      setErrorMessage(null);
    } catch (error) {
      if (!isActiveRef.current) {
        return;
      }
      setErrorMessage(getErrorMessage(error, "Unable to refresh the dashboard."));
    } finally {
      if (isActiveRef.current) {
        setIsRefreshing(false);
      }
    }
  }

  async function refreshContext() {
    try {
      const response = await fetch("/api/context", { cache: "no-store" });
      const payload = (await response.json()) as AppContext | { detail?: string };
      if (!response.ok) {
        throw new Error(readDetail(payload, "Unable to refresh app context."));
      }
      if (isActiveRef.current) {
        setContext(payload as AppContext);
      }
    } catch (error) {
      if (isActiveRef.current) {
        setErrorMessage(getErrorMessage(error, "Unable to refresh app context."));
      }
    }
  }

  async function loadSelectedEvents(ticketId: number | null) {
    if (!ticketId) {
      setSelectedEvents([]);
      return;
    }

    setIsEventsRefreshing(true);
    try {
      const response = await fetch(`/api/tickets/${ticketId}/events`, { cache: "no-store" });
      const payload = (await response.json()) as TicketEvent[] | { detail?: string };
      if (!response.ok) {
        throw new Error(readDetail(payload, "Unable to load ticket events."));
      }
      if (isActiveRef.current) {
        setSelectedEvents(payload as TicketEvent[]);
      }
    } catch (error) {
      if (isActiveRef.current) {
        setErrorMessage(getErrorMessage(error, "Unable to load ticket events."));
      }
    } finally {
      if (isActiveRef.current) {
        setIsEventsRefreshing(false);
      }
    }
  }

  useEffect(() => {
    void refreshDashboard();
    void refreshContext();
    const intervalId = window.setInterval(() => {
      void refreshDashboard();
      void refreshContext();
    }, 10_000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    void loadSelectedEvents(selectedTicketId);
  }, [selectedTicketId]);

  useEffect(() => {
    if (selectedTicket?.resolution_note) {
      setResolutionNote(selectedTicket.resolution_note);
      return;
    }
    setResolutionNote("Resolved manually from the dashboard.");
  }, [selectedTicket?.id, selectedTicket?.resolution_note]);

  const statusCounts = useMemo(() => {
    return deferredTickets.reduce<Record<string, number>>((counts, ticket) => {
      counts[ticket.status] = (counts[ticket.status] ?? 0) + 1;
      return counts;
    }, {});
  }, [deferredTickets]);

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
        throw new Error(readDetail(payload, "Ticket submission failed."));
      }

      const createdTicket = payload as Ticket;
      form.reset();
      setReporterEmail("");
      setTitle("");
      setDescription("");
      setFileNames([]);
      setFeedbackMessage(
        `Ticket #${createdTicket.id} accepted. Solidus triage and mocked integrations are now running.`,
      );
      setSelectedTicketId(createdTicket.id);
      await refreshDashboard();
      await loadSelectedEvents(createdTicket.id);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Ticket submission failed."));
    }
  }

  async function resolveSelectedTicket() {
    if (!selectedTicket) {
      return;
    }

    setFeedbackMessage(null);
    setErrorMessage(null);

    startResolveTransition(() => {
      void resolveTicketRequest(selectedTicket.id, resolutionNote);
    });
  }

  async function resolveTicketRequest(ticketId: number, note: string) {
    try {
      const response = await fetch(`/api/tickets/${ticketId}/resolve`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ resolution_note: note }),
      });
      const payload = (await response.json()) as Ticket | { detail?: string };
      if (!response.ok) {
        throw new Error(readDetail(payload, "Failed to resolve ticket."));
      }

      setFeedbackMessage(`Ticket #${ticketId} marked as resolved and downstream notifications were emitted.`);
      await refreshDashboard();
      await loadSelectedEvents(ticketId);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to resolve ticket."));
    }
  }

  return (
    <main className="dashboard-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Solidus Incident Routing</p>
          <h1>Elephant Agent</h1>
          <p className="hero-copy">
            Multimodal intake for the Solidus open-source e-commerce codebase with guardrails, event
            traces, mocked notifications, and manual resolution tracking.
          </p>
          <div className="hero-tags">
            <span>Target repo: `{context?.ecommerce.codebase_repo_url ?? "solidusio/solidus"}`</span>
            <span>Stages: ingest / triage / ticket / notify / communicator / resolved</span>
            <span>Linear mode: {context?.linear.mode ?? "dry-run"}</span>
          </div>
          <div className="connection-strip">
            <ConnectionCard
              label="Storefront"
              value={context?.ecommerce.storefront_url ?? "Pending connection"}
              href={context?.ecommerce.storefront_url ?? null}
            />
            <ConnectionCard
              label="Admin"
              value={context?.ecommerce.admin_url ?? "Pending connection"}
              href={context?.ecommerce.admin_url ?? null}
            />
            <ConnectionCard
              label="Linear Team"
              value={context?.linear.default_team_name ?? firstEffectiveTeam(context) ?? "Dry-run only"}
              href={null}
            />
          </div>
        </div>
        <div className="stats-grid">
          <StatCard label="Tickets" value={String(summary?.total_tickets ?? deferredTickets.length)} accent="sand" />
          <StatCard label="Resolved" value={String(statusCounts.resolved ?? 0)} accent="mint" />
          <StatCard label="Triage Events" value={String(summary?.stage_counts.triage ?? 0)} accent="sky" />
          <StatCard label="Communicator" value={String(summary?.stage_counts.communicator ?? 0)} accent="coral" />
        </div>
      </section>

      <section className="panel compose-panel">
        <div className="panel-header">
          <div>
            <p className="panel-kicker">New Report</p>
            <h2>Submit a multimodal ticket</h2>
          </div>
          <p className="panel-note">Accepted attachments: .txt, .md, .log, .png, .jpg, .jpeg, .webp</p>
        </div>

        <form className="ticket-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Reporter email</span>
            <input
              name="reporter_email"
              type="email"
              value={reporterEmail}
              onChange={(event) => setReporterEmail(event.target.value)}
              placeholder="ops@store.example"
            />
          </label>

          <label className="field">
            <span>Title</span>
            <input
              name="title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Solidus checkout returns 500 when promotions are applied"
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
              placeholder="Describe symptoms, storefront/admin/API impact, reproduction path, and timing."
              required
            />
          </label>

          <label className="field">
            <span>Attachments</span>
            <input
              name="files"
              type="file"
              accept=".txt,.md,.log,.png,.jpg,.jpeg,.webp"
              multiple
              onChange={handleFileChange}
            />
          </label>

          <div className="file-strip" aria-live="polite">
            {fileNames.length > 0 ? (
              fileNames.map((file) => <span key={file}>{file}</span>)
            ) : (
              <span>No artifacts selected yet.</span>
            )}
          </div>

          <div className="form-actions">
            <button className="submit-button" type="submit" disabled={isPending}>
              {isPending ? "Submitting..." : "Enviar reporte"}
            </button>
            <p className="panel-note">Prompt injection markers are scanned and shown in the event timeline.</p>
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

          <div className="stage-strip">
            {Object.entries(summary?.stage_counts ?? {}).map(([stage, count]) => (
              <span key={stage}>
                {STAGE_LABELS[stage] ?? stage}: {count}
              </span>
            ))}
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
                  <span>Submit the first Solidus report to see the queue and traces.</span>
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

        <TicketDetailPanel
          context={context}
          events={selectedEvents}
          isEventsRefreshing={isEventsRefreshing}
          isResolving={isResolving}
          onResolve={resolveSelectedTicket}
          onResolutionNoteChange={setResolutionNote}
          resolutionNote={resolutionNote}
          ticket={selectedTicket}
        />
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

type TicketDetailPanelProps = {
  context: AppContext | null;
  ticket: Ticket | null;
  events: TicketEvent[];
  isEventsRefreshing: boolean;
  resolutionNote: string;
  onResolutionNoteChange: (value: string) => void;
  onResolve: () => void;
  isResolving: boolean;
};

function TicketDetailPanel({
  context,
  ticket,
  events,
  isEventsRefreshing,
  resolutionNote,
  onResolutionNoteChange,
  onResolve,
  isResolving,
}: TicketDetailPanelProps) {
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
          <span>Analysis, observability traces, attachments, and resolve action will appear here.</span>
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
          <p className="detail-meta">
            Reporter: {ticket.reporter_email || "not provided"} / Trace: {ticket.trace_id}
          </p>
        </article>

        <article className="detail-card">
          <p className="detail-label">Routing</p>
          <p className="detail-copy">
            {TEAM_LABELS[ticket.assigned_team ?? analysis?.assigned_team ?? ""] ?? "Pending"} /{" "}
            {formatPriority(ticket.priority ?? analysis?.priority ?? "medium")}
          </p>
          <p className="detail-meta">
            {analysis
              ? `${analysis.category.toUpperCase()} / ${analysis.solidus_area} / confidence ${Math.round(
                  analysis.confidence * 100,
                )}%`
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
            {analysis?.keywords?.length ? (
              analysis.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)
            ) : (
              <span>Awaiting extraction.</span>
            )}
          </div>
        </article>

        <article className="detail-card">
          <p className="detail-label">Integrations</p>
          <p className="detail-copy">
            Linear: {ticket.linear_issue_id ?? "pending"} / Communicator: {ticket.communicator_status ?? "pending"}
          </p>
          <p className="detail-meta">
            {analysis?.execution_mode === "dry-run"
              ? "Dry-run fallback keeps integrations demoable without secrets."
              : "Live integrations active."}
          </p>
          <p className="detail-meta">Linear target: {resolveLinearTarget(context, ticket.assigned_team)}</p>
        </article>
      </div>

      <article className="detail-section">
        <div className="section-title">
          <h3>Guardrails</h3>
          <span>{ticket.guardrail_findings.length} findings</span>
        </div>
        {ticket.guardrail_findings.length ? (
          <div className="steps-list">
            {ticket.guardrail_findings.map((finding) => (
              <p key={`${finding.rule}-${finding.message}`}>
                [{finding.severity}] {finding.message}
              </p>
            ))}
          </div>
        ) : (
          <div className="empty-inline">No prompt injection markers were detected.</div>
        )}
      </article>

      <article className="detail-section">
        <div className="section-title">
          <h3>Attachments</h3>
          <span>{ticket.attachments.length} artifacts</span>
        </div>
        {ticket.attachments.length ? (
          <div className="attachment-list">
            {ticket.attachments.map((attachment) => (
              <div key={attachment.sha256} className="attachment-card">
                <strong>{attachment.filename}</strong>
                <span>
                  {attachment.kind} / {attachment.mime_type} / {Math.round(attachment.size_bytes / 1024)} KB
                </span>
                {attachment.prompt_injection_signals.length ? (
                  <small>{attachment.prompt_injection_signals.join(" ")}</small>
                ) : (
                  <small>{attachment.text_excerpt || "Image artifact stored for multimodal analysis."}</small>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-inline">No attachments stored for this ticket.</div>
        )}
      </article>

      <article className="detail-section">
        <div className="section-title">
          <h3>Relevant Solidus files</h3>
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
          <div className="empty-inline">No Solidus matches stored for this ticket yet.</div>
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
          <div className="empty-inline">Suggested actions will appear once analysis finishes.</div>
        )}
      </article>

      <article className="detail-section">
        <div className="section-title">
          <h3>Event trace</h3>
          <span>{isEventsRefreshing ? "Refreshing..." : `${events.length} events`}</span>
        </div>
        {events.length ? (
          <div className="event-list">
            {events.map((event) => (
              <div key={event.id} className={`event-card ${event.level}`}>
                <div className="event-head">
                  <strong>{STAGE_LABELS[event.stage] ?? event.stage}</strong>
                  <span>{formatDate(event.created_at)}</span>
                </div>
                <p>{event.message}</p>
                {Object.keys(event.payload ?? {}).length ? (
                  <code>{JSON.stringify(event.payload)}</code>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-inline">No events loaded for this ticket yet.</div>
        )}
      </article>

      <article className="detail-section">
        <div className="section-title">
          <h3>Resolve ticket</h3>
          <span>{ticket.resolved_at ? `Resolved ${formatDate(ticket.resolved_at)}` : "Manual action available"}</span>
        </div>
        <label className="field">
          <span>Resolution note</span>
          <textarea
            rows={4}
            value={resolutionNote}
            onChange={(event) => onResolutionNoteChange(event.target.value)}
          />
        </label>
        <div className="form-actions">
          <button
            className="submit-button secondary"
            type="button"
            disabled={isResolving || ticket.status === "resolved"}
            onClick={onResolve}
          >
            {ticket.status === "resolved" ? "Already resolved" : isResolving ? "Resolving..." : "Mark resolved"}
          </button>
          <p className="panel-note">This emits resolved-stage email and communicator events.</p>
        </div>
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
          <p className="detail-meta">Assigned workspace target: {resolveLinearTarget(context, ticket.assigned_team)}</p>
          {ticket.communicator_reference ? <p className="detail-meta">{ticket.communicator_reference}</p> : null}
          {ticket.error_message ? <p className="message error inline">{ticket.error_message}</p> : null}
        </div>
      </article>
    </aside>
  );
}

function ConnectionCard({ label, value, href }: { label: string; value: string; href: string | null }) {
  const content = (
    <>
      <span>{label}</span>
      <strong>{value}</strong>
    </>
  );

  if (href) {
    return (
      <a className="connection-card" href={href} target="_blank" rel="noreferrer">
        {content}
      </a>
    );
  }

  return <div className="connection-card">{content}</div>;
}

function firstEffectiveTeam(context: AppContext | null) {
  return context?.linear.targets.find((target) => target.effective_team_name)?.effective_team_name ?? null;
}

function resolveLinearTarget(context: AppContext | null, assignedTeam?: string | null) {
  if (!context) {
    return "Not loaded";
  }

  const matchingTarget = context.linear.targets.find((target) => target.slug === assignedTeam);
  return (
    matchingTarget?.effective_team_name ??
    context.linear.default_team_name ??
    firstEffectiveTeam(context) ??
    "Dry-run only"
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

function readDetail(payload: unknown, fallback: string) {
  if (typeof payload === "object" && payload && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
}
