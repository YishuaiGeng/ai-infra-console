import { cookies } from "next/headers";

import {
  centralFetch,
  SESSION_COOKIE,
  webError,
} from "@/lib/server/central-api";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return webError(401, "authentication_required", "Sign in is required.");
  }

  let upstream: Response;
  try {
    upstream = await centralFetch(
      "/api/v1/infrastructure/events",
      { headers: { accept: "text/event-stream" } },
      token,
    );
  } catch {
    return webError(
      502,
      "central_unavailable",
      "The Central API event stream is unavailable.",
    );
  }

  if (!upstream.ok || !upstream.body) {
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  }
  return new Response(upstream.body, {
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache, no-transform",
      "x-accel-buffering": "no",
    },
  });
}
