import { NextResponse } from "next/server";

import { getBackendUrl } from "@/lib/backend";

export const runtime = "nodejs";

function proxyFailure(detail: string, status = 503) {
  return NextResponse.json({ detail }, { status });
}

async function fromBackend(response: Response) {
  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET() {
  try {
    const response = await fetch(`${getBackendUrl()}/api/v1/tickets`, {
      cache: "no-store",
    });
    return fromBackend(response);
  } catch {
    return proxyFailure("Backend unavailable. Start FastAPI and try again.");
  }
}

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const response = await fetch(`${getBackendUrl()}/api/v1/tickets`, {
      method: "POST",
      body: formData,
      cache: "no-store",
    });
    return fromBackend(response);
  } catch {
    return proxyFailure("Ticket submission failed because the backend is unreachable.");
  }
}
