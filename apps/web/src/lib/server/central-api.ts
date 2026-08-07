import "server-only";

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const SESSION_COOKIE = "aic_session";

export interface CentralErrorEnvelope {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: unknown;
  };
}

export function sessionCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict" as const,
    path: "/",
    maxAge,
  };
}

export function centralApiUrl(path: string) {
  const baseUrl =
    process.env.AI_INFRA_API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  return new URL(path, baseUrl).toString();
}

export async function centralFetch(
  path: string,
  init: RequestInit = {},
  token?: string,
) {
  const headers = new Headers(init.headers);
  if (!headers.has("accept")) headers.set("accept", "application/json");
  if (init.body !== undefined) headers.set("content-type", "application/json");
  if (token) headers.set("authorization", `Bearer ${token}`);
  return fetch(centralApiUrl(path), {
    ...init,
    headers,
    cache: "no-store",
  });
}

export function webError(
  status: number,
  code: string,
  message: string,
  requestId = "web",
) {
  return NextResponse.json<CentralErrorEnvelope>(
    { error: { code, message, request_id: requestId } },
    { status },
  );
}

export async function proxyCentral(
  path: string,
  init: RequestInit = {},
): Promise<NextResponse> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return webError(401, "authentication_required", "Sign in is required.");
  }

  let upstream: Response;
  try {
    upstream = await centralFetch(path, init, token);
  } catch {
    return webError(
      502,
      "central_unavailable",
      "The Central API is unavailable.",
    );
  }

  const response = new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: {
      "content-type":
        upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
  const requestId = upstream.headers.get("x-request-id");
  if (requestId) response.headers.set("x-request-id", requestId);
  if (upstream.status === 401) response.cookies.delete(SESSION_COOKIE);
  return response;
}
