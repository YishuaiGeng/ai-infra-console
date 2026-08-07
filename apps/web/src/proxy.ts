import { type NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/server/central-api";

export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/((?!api|login|_next/static|_next/image|favicon.ico|robots.txt).*)",
  ],
};
