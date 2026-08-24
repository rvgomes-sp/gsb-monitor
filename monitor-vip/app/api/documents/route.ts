import { getSql } from "../../../db";
import { requireAuthenticatedSession } from "../../../lib/require-session";

export async function GET(request: Request) {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  const processId = new URL(request.url).searchParams.get("process_id")?.trim() ?? "";
  if (!processId) return Response.json({ error: "Processo obrigatório." }, { status: 400 });
  const sql = getSql();
  const rows = await sql`
    SELECT label, document_type, reading_status, sha256, object_key
    FROM monitor.documents WHERE process_id = ${processId} ORDER BY created_at ASC`;
  return Response.json({
    documents: rows.map((item) => ({
      label: item.label,
      document_type: item.document_type,
      reading_status: item.reading_status,
      sha256: item.sha256,
      url: `/api/document?key=${encodeURIComponent(item.object_key)}`,
    })),
  });
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
