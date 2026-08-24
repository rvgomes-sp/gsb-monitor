import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, verifySessionToken } from "./lib/auth";

const publicPaths = new Set([
  "/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/import/document",
  "/api/import/snapshot",
  "/api/_diag",
  "/og.png",
  "/favicon.ico",
]);

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (
    publicPaths.has(pathname) ||
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/.well-known/")
  ) {
    return NextResponse.next();
  }

  const secret = process.env.PORTAL_AUTH_SECRET ?? "";
  const token = request.cookies.get(SESSION_COOKIE)?.value ?? "";
  const session = secret && token ? await verifySessionToken(token, secret) : null;
  if (session) {
    const response = NextResponse.next();
    response.headers.set("Cache-Control", "private, no-store, max-age=0");
    response.headers.set("Pragma", "no-cache");
    return response;
  }

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "Sessão não autenticada." }, { status: 401 });
  }
  const login = new URL("/login", request.url);
  login.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};
