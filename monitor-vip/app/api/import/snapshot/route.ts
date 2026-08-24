import { getSql } from "../../../../db";
import { ensureDatabase } from "../../../../db/runtime";

function authorized(request: Request) {
  const token = process.env.IMPORT_TOKEN ?? "";
  const supplied = request.headers.get("x-import-token") ?? "";
  return Boolean(token) && supplied === token;
}

export async function POST(request: Request) {
  if (!authorized(request)) return Response.json({ error: "Não autorizado." }, { status: 401 });
  await ensureDatabase();
  const sql = getSql();
  const payload = await request.json() as {
    feed?: Record<string, unknown> & { opportunities?: Array<Record<string, unknown>> };
    operations?: {
      outreach?: Record<string, Record<string, unknown>>;
      proposals?: Array<Record<string, unknown>>;
      counters?: Record<string, number>;
      document_jobs?: Record<string, Record<string, unknown>>;
    };
  };
  const feed = payload.feed ?? {};
  const opportunityRows = feed.opportunities ?? [];
  const metadata = { ...feed };
  delete metadata.opportunities;
  const now = new Date().toISOString();

  // ---- oportunidades (substituição total) ----
  await sql`DELETE FROM monitor.opportunities`;
  for (let position = 0; position < opportunityRows.length; position += 1) {
    const item = opportunityRows[position];
    const processId = String(item.processo ?? "");
    const supplierCnpj = String(item.fornecedor_cnpj ?? "");
    await sql`INSERT INTO monitor.opportunities(
      id,position,process_id,supplier_cnpj,route,contract_value,payload_json,updated_at
    ) VALUES(
      ${`${processId}|${supplierCnpj}|${position}`}, ${position}, ${processId},
      ${supplierCnpj}, ${String(item.rota ?? "")}, ${Number(item.valor_numero ?? 0)},
      ${JSON.stringify(item)}, ${now}
    )`;
  }
  await sql`INSERT INTO monitor.feed_metadata(id,payload_json,updated_at)
    VALUES(1, ${JSON.stringify(metadata)}, ${now})
    ON CONFLICT(id) DO UPDATE SET
      payload_json=excluded.payload_json, updated_at=excluded.updated_at`;

  // ---- operações ----
  const operations = payload.operations ?? {};
  for (const [processId, raw] of Object.entries(operations.outreach ?? {})) {
    const value = (snake: string, camel?: string) =>
      String(raw[snake] ?? (camel ? raw[camel] : "") ?? "");
    await sql`INSERT INTO monitor.outreach(
      process_id,status,decision_maker,email,phone,last_contact_at,sent_at,
      next_follow_up_at,subject,body,notes,operator,created_at,updated_at
    ) VALUES(
      ${processId}, ${value("status") || "NAO_INICIADO"},
      ${value("decision_maker", "decisionMaker")}, ${value("email")}, ${value("phone")},
      ${value("last_contact_at", "lastContactAt")}, ${value("sent_at", "sentAt")},
      ${value("next_follow_up_at", "nextFollowUpAt")}, ${value("subject")}, ${value("body")},
      ${value("notes")}, ${value("operator") || "Ana Fonseca"},
      ${value("created_at", "createdAt") || now}, ${value("updated_at", "updatedAt") || now}
    ) ON CONFLICT(process_id) DO UPDATE SET
      status=excluded.status,decision_maker=excluded.decision_maker,
      email=excluded.email,phone=excluded.phone,last_contact_at=excluded.last_contact_at,
      sent_at=excluded.sent_at,next_follow_up_at=excluded.next_follow_up_at,
      subject=excluded.subject,body=excluded.body,notes=excluded.notes,
      operator=excluded.operator,updated_at=excluded.updated_at`;

    await sql`DELETE FROM monitor.outreach_history WHERE process_id = ${processId}`;
    const history = Array.isArray(raw.history) ? raw.history : [];
    for (const entry of history) {
      const h = entry as Record<string, unknown>;
      await sql`INSERT INTO monitor.outreach_history(
        process_id,at,event,fields_json,status,operator
      ) VALUES(
        ${processId}, ${String(h.at ?? now)}, ${String(h.event ?? "OUTREACH_UPDATED")},
        ${JSON.stringify(h.fields ?? [])}, ${String(h.status ?? raw.status ?? "NAO_INICIADO")},
        ${String(h.operator ?? raw.operator ?? "Ana Fonseca")}
      )`;
    }
  }

  await sql`DELETE FROM monitor.proposals`;
  for (const raw of operations.proposals ?? []) {
    const v = (snake: string, camel?: string) => raw[snake] ?? (camel ? raw[camel] : undefined);
    await sql`INSERT INTO monitor.proposals(
      number,created_at,status,process_id,supplier,supplier_cnpj,agency,tender,
      administrative_process,decision_maker,contract_value,guarantee_percentage,
      insured_amount,annual_rate,term_months,estimated_premium,notes,operator
    ) VALUES(
      ${String(v("number") ?? "")}, ${String(v("created_at", "createdAt") ?? now)},
      ${String(v("status") ?? "GERADA")}, ${String(v("process_id", "processId") ?? "")},
      ${String(v("supplier") ?? "")}, ${String(v("supplier_cnpj", "supplierCnpj") ?? "")},
      ${String(v("agency") ?? "")}, ${String(v("tender") ?? "")},
      ${String(v("administrative_process", "administrativeProcess") ?? "")},
      ${String(v("decision_maker", "decisionMaker") ?? "")},
      ${Number(v("contract_value", "contractValue") ?? 0)},
      ${Number(v("guarantee_percentage", "guaranteePercentage") ?? 0)},
      ${Number(v("insured_amount", "insuredAmount") ?? 0)},
      ${Number(v("annual_rate", "annualRate") ?? 0)},
      ${Number(v("term_months", "termMonths") ?? 0)},
      ${Number(v("estimated_premium", "estimatedPremium") ?? 0)},
      ${String(v("notes") ?? "")}, ${String(v("operator") ?? "Ana Fonseca")}
    )`;
  }

  for (const [key, value] of Object.entries(operations.counters ?? {})) {
    await sql`INSERT INTO monitor.counters(key,value) VALUES(${key}, ${Number(value)})
      ON CONFLICT(key) DO UPDATE SET value=GREATEST(monitor.counters.value, excluded.value)`;
  }

  for (const [processId, raw] of Object.entries(operations.document_jobs ?? {})) {
    const status = String(raw.status ?? "");
    const requestedAt = String(raw.requested_at ?? raw.requestedAt ?? now);
    const updatedAt = String(raw.updated_at ?? raw.updatedAt ?? now);
    await sql`INSERT INTO monitor.document_jobs(
      process_id,status,requested_at,updated_at,payload_json
    ) VALUES(${processId}, ${status}, ${requestedAt}, ${updatedAt}, ${JSON.stringify(raw)})
    ON CONFLICT(process_id) DO UPDATE SET
      status=excluded.status,requested_at=excluded.requested_at,
      updated_at=excluded.updated_at,payload_json=excluded.payload_json`;
  }

  return Response.json({
    status: "OK",
    opportunities: opportunityRows.length,
    outreach: Object.keys(operations.outreach ?? {}).length,
    history: Object.values(operations.outreach ?? {}).reduce(
      (total, item) => total + (Array.isArray(item.history) ? item.history.length : 0),
      0,
    ),
    proposals: (operations.proposals ?? []).length,
  });
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
