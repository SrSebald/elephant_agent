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
    const response = await fetch(`${getBackendUrl()}/api/v1/context`, {
      cache: "no-store",
    });
    return fromBackend(response);
  } catch {
    return proxyFailure("Context loading failed because the backend is unreachable.");
  }
}
