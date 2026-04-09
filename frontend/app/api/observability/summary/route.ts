import { NextResponse } from "next/server";

import { getBackendUrl } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET() {
  try {
    const response = await fetch(`${getBackendUrl()}/api/v1/tickets/observability/summary`, {
      cache: "no-store",
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Unable to load observability summary." }, { status: 503 });
  }
}
