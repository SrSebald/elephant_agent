export type TicketStatus = "queued" | "processing" | "routed" | "resolved" | "failed";
export type TicketPriority = "low" | "medium" | "high" | "critical";
export type TicketTeam = "core" | "admin" | "api";

export interface RelevantFile {
  repository: string;
  path: string;
  url?: string | null;
  snippet: string;
  content_excerpt: string;
  score: number;
}

export interface GuardrailFinding {
  rule: string;
  severity: "info" | "warning" | "high";
  message: string;
}

export interface AttachmentArtifact {
  filename: string;
  kind: "text" | "image";
  mime_type: string;
  size_bytes: number;
  sha256: string;
  text_excerpt: string;
  prompt_injection_signals: string[];
}

export interface TicketAnalysis {
  category: "bug" | "incident" | "config";
  summary: string;
  diagnosis: string;
  resolution_path: string;
  assigned_team: TicketTeam;
  priority: TicketPriority;
  keywords: string[];
  components: string[];
  solidus_area: string;
  next_steps: string[];
  confidence: number;
  execution_mode: "live" | "dry-run";
  guardrail_notes: string[];
}

export interface Ticket {
  id: number;
  title: string;
  reporter_email?: string | null;
  description: string;
  file_content: string;
  trace_id: string;
  status: TicketStatus;
  analysis: TicketAnalysis | null;
  guardrail_findings: GuardrailFinding[];
  resolution_path?: string | null;
  relevant_files: RelevantFile[];
  attachments: AttachmentArtifact[];
  linear_issue_id?: string | null;
  linear_issue_url?: string | null;
  communicator_status?: string | null;
  communicator_reference?: string | null;
  assigned_team?: string | null;
  priority?: string | null;
  error_message?: string | null;
  resolution_note?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketEvent {
  id: number;
  ticket_id?: number | null;
  trace_id: string;
  stage: "ingest" | "guardrails" | "triage" | "ticket" | "notify" | "communicator" | "resolved" | "system";
  level: "info" | "warning" | "error";
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ObservabilitySummary {
  total_tickets: number;
  status_counts: Record<string, number>;
  stage_counts: Record<string, number>;
  latest_event_at?: string | null;
}

export interface EcommerceContext {
  name: string;
  platform: string;
  storefront_url?: string | null;
  admin_url?: string | null;
  support_email?: string | null;
  codebase_repo_url: string;
  codebase_branch: string;
}

export interface LinearTeamTarget {
  slug: string;
  display_name: string;
  configured_team_id?: string | null;
  effective_team_id?: string | null;
  effective_team_name?: string | null;
}

export interface LinearContext {
  connected: boolean;
  mode: "live" | "dry-run";
  default_team_id?: string | null;
  default_team_name?: string | null;
  targets: LinearTeamTarget[];
}

export interface AppContext {
  ecommerce: EcommerceContext;
  linear: LinearContext;
}
