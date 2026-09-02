import { getSql } from "../../../db";
import { requireAuthenticatedSession } from "../../../lib/require-session";

// Uma leitura consistente da memória existente; nunca grava nem inicializa schema.
// A consulta única elimina a fila de quatro consultas concorrentes na conexão max:1.
export async function GET() {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  let sql: ReturnType<typeof getSql> | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    sql = getSql();
    const query = sql`
      SELECT jsonb_build_object(
        'version', 2, 'storage', 'Supabase', 'updated_at', now(),
        'outreach', (SELECT coalesce(jsonb_object_agg(o.process_id,
          to_jsonb(o) || jsonb_build_object('history', (
            SELECT coalesce(jsonb_agg(jsonb_build_object(
              'at', h.at, 'event', h.event, 'fields', h.fields_json::jsonb,
              'status', h.status, 'operator', h.operator
            ) ORDER BY h.id), '[]'::jsonb)
            FROM monitor.outreach_history h WHERE h.process_id = o.process_id
          ))), '{}'::jsonb) FROM monitor.outreach o),
        'proposals', (SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY p.created_at, p.number), '[]'::jsonb) FROM monitor.proposals p),
        'document_jobs', (SELECT coalesce(jsonb_object_agg(j.process_id, j.payload_json::jsonb), '{}'::jsonb) FROM monitor.document_jobs j),
        'counters', (SELECT coalesce(jsonb_object_agg(c.key, c.value), '{}'::jsonb) FROM monitor.counters c)
      ) AS payload
    `;
    const result = await Promise.race([
      query,
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error("OPERATIONAL_READ_TIMEOUT")), 15000);
      }),
    ]);
    return Response.json(result[0].payload, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    // Não enviar strings de conexão, consultas ou dados pessoais nos erros.
    return Response.json({ error: "Memória operacional indisponível. Tente novamente." }, {
      status: 503, headers: { "Cache-Control": "private, no-store" },
    });
  } finally {
    if (timer) clearTimeout(timer);
    if (sql) await sql.end({ timeout: 1 }).catch(() => {});
  }
}
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
