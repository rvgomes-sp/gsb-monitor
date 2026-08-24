import { asc, eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { ensureDatabase } from "../../../db/runtime";
import { documents } from "../../../db/schema";
import { requireAuthenticatedSession } from "../../../lib/require-session";

export async function GET(request: Request) {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  await ensureDatabase();
  const processId = new URL(request.url).searchParams.get("process_id")?.trim() ?? "";
  if (!processId) return Response.json({ error: "Processo obrigatório." }, { status: 400 });
  const rows = await getDb().select().from(documents)
    .where(eq(documents.processId, processId))
    .orderBy(asc(documents.createdAt));
  return Response.json({
    documents: rows.map((item) => ({
      label: item.label,
      document_type: item.documentType,
      reading_status: item.readingStatus,
      sha256: item.sha256,
      url: `/api/document?key=${encodeURIComponent(item.objectKey)}`,
    })),
  });
}
