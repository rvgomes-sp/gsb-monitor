import { asc } from "drizzle-orm";
import { getDb } from "../../../db";
import { ensureDatabase } from "../../../db/runtime";
import { documents, feedMetadata, opportunities } from "../../../db/schema";
import { requireAuthenticatedSession } from "../../../lib/require-session";

export async function GET() {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  try {
    await ensureDatabase();
    const db = getDb();
    const [metadataRows, rows, documentRows] = await Promise.all([
      db.select().from(feedMetadata),
      db.select().from(opportunities).orderBy(asc(opportunities.position)),
      db.select().from(documents).orderBy(asc(documents.createdAt)),
    ]);
    if (!rows.length) {
      return Response.json({ error: "Feed ainda não sincronizado." }, { status: 404 });
    }
    const metadata = metadataRows[0]
      ? JSON.parse(metadataRows[0].payloadJson)
      : {};
    const documentsByProcess = new Map<string, Array<{ label: string; url: string }>>();
    for (const document of documentRows) {
      const list = documentsByProcess.get(document.processId) ?? [];
      list.push({
        label: document.label,
        url: `/api/document?key=${encodeURIComponent(document.objectKey)}`,
      });
      documentsByProcess.set(document.processId, list);
    }
    return Response.json({
      ...metadata,
      opportunities: rows.map((row) => {
        const item = JSON.parse(row.payloadJson);
        return {
          ...item,
          documentos: documentsByProcess.get(row.processId) ?? item.documentos ?? [],
        };
      }),
      cloud: { storage: "D1", updated_at: metadataRows[0]?.updatedAt ?? "" },
    });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Falha ao carregar oportunidades." },
      { status: 500 },
    );
  }
}
