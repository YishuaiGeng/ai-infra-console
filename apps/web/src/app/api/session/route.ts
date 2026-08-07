import { NextResponse } from "next/server";

import {
  proxyCentral,
  SESSION_COOKIE,
} from "@/lib/server/central-api";

export async function GET() {
  return proxyCentral("/api/v1/auth/me");
}

export async function DELETE() {
  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
