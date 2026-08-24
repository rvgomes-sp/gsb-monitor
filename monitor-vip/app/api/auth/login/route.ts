import { NextResponse } from "next/server";
import {
  configuredAccounts,
  createSessionToken,
  portalProfile,
  SESSION_COOKIE,
  sha256,
} from "../../../../lib/auth";

export async function POST(request: Request) {
  const payload = await request.json().catch(() => ({})) as {
    email?: string;
    password?: string;
  };
  const email = String(payload.email ?? "").trim().toLowerCase();
  const password = String(payload.password ?? "");
  const accounts = configuredAccounts();
  const expected = accounts[email];
  const supplied = await sha256(password);
  if (!expected || expected !== supplied) {
    return Response.json({ error: "E-mail ou senha inválidos." }, { status: 401 });
  }
  const secret = process.env.PORTAL_AUTH_SECRET;
  if (!secret) {
    return Response.json({ error: "Autenticação não configurada." }, { status: 503 });
  }
  const token = await createSessionToken(email, secret);
  const response = NextResponse.json(
    { status: "OK", user: portalProfile(email) },
    { headers: { "Cache-Control": "private, no-store, max-age=0" } },
  );
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 12 * 60 * 60,
  });
  return response;
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
