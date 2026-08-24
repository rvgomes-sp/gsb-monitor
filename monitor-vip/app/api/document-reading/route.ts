import { getSql } from "../../../db";
import { requireAuthenticatedSession } from "../../../lib/require-session";

export async function POST(request: Request) {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  const payload = await request.json() as { process_id?: string };
  const processId = String(payload.process_id ?? "").trim();
  if (!processId) return Response.json({ error: "Processo obrigatório." }, { status: 400 });
  const sql = getSql();
  const rows = await sql`SELECT id FROM monitor.documents WHERE process_id = ${processId}`;
  if (!rows.length) {
    return Response.json(
      { error: "O edital ainda não foi enviado pela ponte local." },
      { status: 409 },
    );
  }
  const now = new Date().toISOString();
  const job = {
    process_id: processId,
    status: "CONCLUIDO",
    requested_at: now,
    updated_at: now,
    message: `${rows.length} arquivo(s) disponível(is) na nuvem.`,
  };
  await sql`INSERT INTO monitor.document_jobs(process_id,status,requested_at,updated_at,payload_json)
    VALUES(${processId}, ${job.status}, ${now}, ${now}, ${JSON.stringify(job)})
    ON CONFLICT(process_id) DO UPDATE SET
      status=excluded.status, requested_at=excluded.requested_at,
      updated_at=excluded.updated_at, payload_json=excluded.payload_json`;
  return Response.json({ status: "OK", job });
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
