import { env } from "cloudflare:workers";
import { requireAuthenticatedSession } from "../../../lib/require-session";

export async function GET(request: Request) {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  const key = new URL(request.url).searchParams.get("key")?.trim() ?? "";
  if (!key || !key.startsWith("editais/")) {
    return Response.json({ error: "Documento inválido." }, { status: 400 });
  }
  const object = await env.DOCUMENTS.get(key);
  if (!object) return Response.json({ error: "Documento não localizado." }, { status: 404 });
  return new Response(object.body, {
    headers: {
      "content-type": object.httpMetadata?.contentType ?? "application/octet-stream",
      "content-disposition": `inline; filename="${key.split("/").pop()?.replace(/"/g, "") ?? "documento"}"`,
      "cache-control": "private, max-age=300",
    },
  });
}
