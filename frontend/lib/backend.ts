import type { Ticket } from "@/lib/types";

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
