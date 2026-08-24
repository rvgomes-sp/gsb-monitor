import { cookies } from "next/headers";
import { getSql } from "../../../db";
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
    const sql = getSql();
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
    const prev = (await sql`SELECT * FROM monitor.outreach WHERE process_id = ${processId}`)[0];
    const operator = await authenticatedOperator(data.operator ?? prev?.operator);
    const rec = {
      status,
      decision_maker: String(data.decision_maker ?? prev?.decision_maker ?? "").trim(),
      email: String(data.email ?? prev?.email ?? "").trim(),
      phone: String(data.phone ?? prev?.phone ?? "").trim(),
      last_contact_at: String(data.last_contact_at ?? prev?.last_contact_at ?? "").trim(),
      sent_at: String(data.sent_at ?? prev?.sent_at ?? (status === "ENVIADO" ? now : "")).trim(),
      next_follow_up_at: String(data.next_follow_up_at ?? prev?.next_follow_up_at ?? "").trim(),
      subject: String(data.subject ?? prev?.subject ?? "").trim(),
      body: String(data.body ?? prev?.body ?? "").trim(),
      notes: String(data.notes ?? prev?.notes ?? "").trim(),
      operator,
      created_at: prev?.created_at ?? now,
      updated_at: now,
    };
    await sql`INSERT INTO monitor.outreach(
      process_id,status,decision_maker,email,phone,last_contact_at,sent_at,
      next_follow_up_at,subject,body,notes,operator,created_at,updated_at
    ) VALUES(
      ${processId}, ${rec.status}, ${rec.decision_maker}, ${rec.email}, ${rec.phone},
      ${rec.last_contact_at}, ${rec.sent_at}, ${rec.next_follow_up_at}, ${rec.subject},
      ${rec.body}, ${rec.notes}, ${rec.operator}, ${rec.created_at}, ${rec.updated_at}
    ) ON CONFLICT(process_id) DO UPDATE SET
      status=excluded.status, decision_maker=excluded.decision_maker, email=excluded.email,
      phone=excluded.phone, last_contact_at=excluded.last_contact_at, sent_at=excluded.sent_at,
      next_follow_up_at=excluded.next_follow_up_at, subject=excluded.subject, body=excluded.body,
      notes=excluded.notes, operator=excluded.operator, updated_at=excluded.updated_at`;
    await sql`INSERT INTO monitor.outreach_history(process_id,at,event,fields_json,status,operator)
      VALUES(${processId}, ${now}, ${"OUTREACH_UPDATED"},
             ${JSON.stringify(Object.keys(data).sort())}, ${status}, ${rec.operator})`;
    return Response.json({ status: "OK", record: { processId, ...rec } });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Falha ao salvar." },
      { status: 500 },
    );
  }
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
