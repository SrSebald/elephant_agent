import type { AppContext, ObservabilitySummary, Ticket } from "@/lib/types";

const BACKEND_URL = (process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export function getBackendUrl() {
  return BACKEND_URL;
}

export async function loadInitialTickets(): Promise<Ticket[]> {
  try {
    const response = await fetch(`${getBackendUrl()}/api/v1/tickets`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return [];
    }

    return (await response.json()) as Ticket[];
  } catch {
    return [];
  }
}

export async function loadInitialSummary(): Promise<ObservabilitySummary | null> {
  try {
    const response = await fetch(`${getBackendUrl()}/api/v1/tickets/observability/summary`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }

    return (await response.json()) as ObservabilitySummary;
  } catch {
    return null;
  }
}

export async function loadInitialContext(): Promise<AppContext | null> {
  try {
    const response = await fetch(`${getBackendUrl()}/api/v1/context`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }

    return (await response.json()) as AppContext;
  } catch {
    return null;
  }
}
