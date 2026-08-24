import { cookies } from "next/headers";
import {
  portalProfile,
  SESSION_COOKIE,
  verifySessionToken,
} from "../../../../lib/auth";

export async function GET() {
  const secret = process.env.PORTAL_AUTH_SECRET ?? "";
  const token = (await cookies()).get(SESSION_COOKIE)?.value ?? "";
  const session = secret && token
    ? await verifySessionToken(token, secret)
    : null;

  if (!session) {
    return Response.json(
      { error: "Sessão não autenticada." },
      {
        status: 401,
        headers: { "Cache-Control": "private, no-store, max-age=0" },
      },
    );
  }

  return Response.json(
    { user: portalProfile(session.email) },
    { headers: { "Cache-Control": "private, no-store, max-age=0" } },
  );
}
