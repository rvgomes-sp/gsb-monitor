import { eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { ensureDatabase } from "../../../db/runtime";
import { documentJobs, documents } from "../../../db/schema";
import { requireAuthenticatedSession } from "../../../lib/require-session";

export async function POST(request: Request) {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  await ensureDatabase();
  const payload = await request.json() as { process_id?: string };
  const processId = String(payload.process_id ?? "").trim();
  if (!processId) return Response.json({ error: "Processo obrigatório." }, { status: 400 });
  const db = getDb();
  const rows = await db.select().from(documents)
    .where(eq(documents.processId, processId));
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
  await db.insert(documentJobs).values({
    processId,
    status: job.status,
    requestedAt: now,
    updatedAt: now,
    payloadJson: JSON.stringify(job),
  }).onConflictDoUpdate({
    target: documentJobs.processId,
    set: {
      status: job.status,
      requestedAt: now,
      updatedAt: now,
      payloadJson: JSON.stringify(job),
    },
  });
  return Response.json({ status: "OK", job });
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
