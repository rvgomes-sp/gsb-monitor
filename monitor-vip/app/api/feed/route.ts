import { getSql } from "../../../db";
import { requireAuthenticatedSession } from "../../../lib/require-session";

// SQL cru (postgres-js) — o pooler de transação do Supabase não suporta os
// prepared statements que o drizzle emite; raw sql é o caminho comprovado.
export async function GET() {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  try {
    const sql = getSql();
    const [metaRows, rows, documentRows] = await Promise.all([
      sql`SELECT payload_json, updated_at FROM monitor.feed_metadata WHERE id = 1`,
      sql`SELECT id, process_id, supplier_cnpj, payload_json FROM monitor.opportunities ORDER BY position ASC`,
      sql`SELECT process_id, label, object_key FROM monitor.documents ORDER BY created_at ASC`,
    ]);
    if (!rows.length) {
      return Response.json({ error: "Feed ainda não sincronizado." }, { status: 404 });
    }
    const metadata = metaRows[0]?.payload_json ? JSON.parse(metaRows[0].payload_json) : {};
    const documentsByProcess = new Map<string, Array<{ label: string; url: string }>>();
    for (const document of documentRows) {
      const list = documentsByProcess.get(document.process_id) ?? [];
      list.push({
        label: document.label,
        url: `/api/document?key=${encodeURIComponent(document.object_key)}`,
      });
      documentsByProcess.set(document.process_id, list);
    }
    return Response.json({
      ...metadata,
      opportunities: rows.map((row) => {
        const item = JSON.parse(row.payload_json);
        return {
          ...item,
          // Identidade persistida atual; não reconstruir a partir de processo/posição.
          case_id: row.id,
          processo: row.process_id,
          fornecedor_cnpj: row.supplier_cnpj,
          documentos: documentsByProcess.get(row.process_id) ?? item.documentos ?? [],
        };
      }),
      cloud: { storage: "Supabase", updated_at: metaRows[0]?.updated_at ?? "" },
    });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Falha ao carregar oportunidades." },
      { status: 500 },
    );
  }
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
