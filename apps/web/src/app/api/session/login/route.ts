import { NextResponse } from "next/server";
import { z } from "zod";

import {
  centralFetch,
  SESSION_COOKIE,
  sessionCookieOptions,
  webError,
} from "@/lib/server/central-api";

const loginSchema = z.object({
  username: z.string().trim().min(1).max(64),
  password: z.string().min(1).max(256),
});

interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export async function POST(request: Request) {
  const parsed = loginSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return webError(422, "validation_error", "Enter a username and password.");
  }

  let upstream: Response;
  try {
    upstream = await centralFetch("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(parsed.data),
    });
  } catch {
    return webError(
      502,
      "central_unavailable",
      "The Central API is unavailable.",
    );
  }

  if (!upstream.ok) {
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  }

  const token = (await upstream.json()) as TokenResponse;
  const response = NextResponse.json({ authenticated: true });
  response.cookies.set(
    SESSION_COOKIE,
    token.access_token,
    sessionCookieOptions(token.expires_in),
  );
  return response;
}
