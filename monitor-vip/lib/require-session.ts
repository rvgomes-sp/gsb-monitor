import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "./auth";

export type SessionGuard =
  | { ok: true; email: string }
  | { ok: false; response: Response };

export async function requireAuthenticatedSession(): Promise<SessionGuard> {
  const secret = process.env.PORTAL_AUTH_SECRET ?? "";
  if (!secret) {
    return {
      ok: false,
      response: Response.json(
        { error: "Autenticação não configurada." },
        {
          status: 503,
          headers: { "Cache-Control": "private, no-store, max-age=0" },
        },
      ),
    };
  }
  const token = (await cookies()).get(SESSION_COOKIE)?.value ?? "";
  const session = token ? await verifySessionToken(token, secret) : null;
  if (!session) {
    return {
      ok: false,
      response: Response.json(
        { error: "Sessão não autenticada." },
        {
          status: 401,
          headers: { "Cache-Control": "private, no-store, max-age=0" },
        },
      ),
    };
  }
  return { ok: true, email: session.email };
}
