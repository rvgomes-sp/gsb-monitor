import { cookies } from "next/headers";
import { eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { ensureDatabase } from "../../../db/runtime";
import { outreach, outreachHistory } from "../../../db/schema";
import {
  portalProfile,
  SESSION_COOKIE,
  verifySessionToken,
} from "../../../lib/auth";
import { requireAuthenticatedSession } from "../../../lib/require-session";

const allowedStatuses = new Set([
  "NAO_INICIADO", "EM_PREPARACAO", "PRONTO_PARA_ENVIO", "ENVIADO",
  "AGUARDANDO_RETORNO", "RESPONDEU", "PROPOSTA_EM_PREPARACAO",
  "PROPOSTA_ENVIADA", "NEGOCIACAO", "FECHADO", "SEM_INTERESSE",
]);

async function authenticatedOperator(fallback: unknown) {
  const secret = process.env.PORTAL_AUTH_SECRET ?? "";
  const token = (await cookies()).get(SESSION_COOKIE)?.value ?? "";
  const session = secret && token ? await verifySessionToken(token, secret) : null;
  return session
    ? portalProfile(session.email).name
    : String(fallback ?? "Usuário autenticado").trim();
}

export async function POST(request: Request) {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  try {
    await ensureDatabase();
    const payload = await request.json() as {
      process_id?: string;
      data?: Record<string, unknown>;
    };
    const processId = String(payload.process_id ?? "").trim();
    const data = payload.data ?? {};
    const status = String(data.status ?? "NAO_INICIADO");
    if (!processId) return Response.json({ error: "Processo obrigatório." }, { status: 400 });
    if (!allowedStatuses.has(status)) {
      return Response.json({ error: "Situação operacional inválida." }, { status: 400 });
    }

    const now = new Date().toISOString();
    const db = getDb();
    const [previous] = await db.select().from(outreach).where(eq(outreach.processId, processId));
    const operator = await authenticatedOperator(data.operator ?? previous?.operator);
    const record = {
      processId,
      status,
      decisionMaker: String(data.decision_maker ?? previous?.decisionMaker ?? "").trim(),
      email: String(data.email ?? previous?.email ?? "").trim(),
      phone: String(data.phone ?? previous?.phone ?? "").trim(),
      lastContactAt: String(data.last_contact_at ?? previous?.lastContactAt ?? "").trim(),
      sentAt: String(
        data.sent_at ??
        previous?.sentAt ??
        (status === "ENVIADO" ? now : ""),
      ).trim(),
      nextFollowUpAt: String(data.next_follow_up_at ?? previous?.nextFollowUpAt ?? "").trim(),
      subject: String(data.subject ?? previous?.subject ?? "").trim(),
      body: String(data.body ?? previous?.body ?? "").trim(),
      notes: String(data.notes ?? previous?.notes ?? "").trim(),
      operator,
      createdAt: previous?.createdAt ?? now,
      updatedAt: now,
    };
    await db.insert(outreach).values(record).onConflictDoUpdate({
      target: outreach.processId,
      set: {
        status: record.status,
        decisionMaker: record.decisionMaker,
        email: record.email,
        phone: record.phone,
        lastContactAt: record.lastContactAt,
        sentAt: record.sentAt,
        nextFollowUpAt: record.nextFollowUpAt,
        subject: record.subject,
        body: record.body,
        notes: record.notes,
        operator: record.operator,
        updatedAt: record.updatedAt,
      },
    });
    await db.insert(outreachHistory).values({
      processId,
      at: now,
      event: "OUTREACH_UPDATED",
      fieldsJson: JSON.stringify(Object.keys(data).sort()),
      status,
      operator: record.operator,
    });
    return Response.json({ status: "OK", record });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Falha ao salvar." },
      { status: 500 },
    );
  }
}
