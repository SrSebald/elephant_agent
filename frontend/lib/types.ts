export type TicketStatus = "queued" | "processing" | "routed" | "failed";
export type TicketPriority = "low" | "medium" | "high" | "critical";
export type TicketTeam = "backend" | "frontend" | "infra";

export interface RelevantFile {
  repository: string;
  path: string;
  url?: string | null;
  snippet: string;
  content_excerpt: string;
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
  next_steps: string[];
  confidence: number;
  execution_mode: "live" | "dry-run";
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  file_content: string;
  status: TicketStatus;
  analysis: TicketAnalysis | null;
  resolution_path?: string | null;
  relevant_files: RelevantFile[];
  linear_issue_id?: string | null;
  linear_issue_url?: string | null;
  assigned_team?: string | null;
  priority?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}
