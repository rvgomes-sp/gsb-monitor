import { env } from "cloudflare:workers";
import { ensureDatabase } from "../../../../db/runtime";

function authorized(request: Request) {
  const supplied = request.headers.get("x-import-token") ?? "";
  return Boolean(env.IMPORT_TOKEN) && supplied === env.IMPORT_TOKEN;
}

export async function POST(request: Request) {
  if (!authorized(request)) return Response.json({ error: "Não autorizado." }, { status: 401 });
  await ensureDatabase();
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

  await env.DB.prepare("DELETE FROM opportunities").run();
  const statements = opportunityRows.map((item, position) => {
    const processId = String(item.processo ?? "");
    const supplierCnpj = String(item.fornecedor_cnpj ?? "");
    return env.DB.prepare(`INSERT INTO opportunities(
      id,position,process_id,supplier_cnpj,route,contract_value,payload_json,updated_at
    ) VALUES(?,?,?,?,?,?,?,?)`).bind(
      `${processId}|${supplierCnpj}|${position}`,
      position,
      processId,
      supplierCnpj,
      String(item.rota ?? ""),
      Number(item.valor_numero ?? 0),
      JSON.stringify(item),
      now,
    );
  });
  for (let index = 0; index < statements.length; index += 50) {
    await env.DB.batch(statements.slice(index, index + 50));
  }
  await env.DB.prepare(`INSERT INTO feed_metadata(id,payload_json,updated_at)
    VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET
    payload_json=excluded.payload_json,updated_at=excluded.updated_at`)
    .bind(JSON.stringify(metadata), now).run();

  const operations = payload.operations ?? {};
  for (const [processId, raw] of Object.entries(operations.outreach ?? {})) {
    const value = (snake: string, camel?: string) =>
      String(raw[snake] ?? (camel ? raw[camel] : "") ?? "");
    await env.DB.prepare(`INSERT INTO outreach(
      process_id,status,decision_maker,email,phone,last_contact_at,sent_at,
      next_follow_up_at,subject,body,notes,operator,created_at,updated_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(process_id) DO UPDATE SET
      status=excluded.status,decision_maker=excluded.decision_maker,
      email=excluded.email,phone=excluded.phone,last_contact_at=excluded.last_contact_at,
      sent_at=excluded.sent_at,next_follow_up_at=excluded.next_follow_up_at,
      subject=excluded.subject,body=excluded.body,notes=excluded.notes,
      operator=excluded.operator,updated_at=excluded.updated_at`).bind(
        processId,
        value("status") || "NAO_INICIADO",
        value("decision_maker", "decisionMaker"),
        value("email"), value("phone"),
        value("last_contact_at", "lastContactAt"),
        value("sent_at", "sentAt"),
        value("next_follow_up_at", "nextFollowUpAt"),
        value("subject"), value("body"), value("notes"),
        value("operator") || "Ana Fonseca",
        value("created_at", "createdAt") || now,
        value("updated_at", "updatedAt") || now,
      ).run();

    await env.DB.prepare("DELETE FROM outreach_history WHERE process_id = ?")
      .bind(processId).run();
    const history = Array.isArray(raw.history) ? raw.history : [];
    for (const entry of history) {
      const historyRow = entry as Record<string, unknown>;
      await env.DB.prepare(`INSERT INTO outreach_history(
        process_id,at,event,fields_json,status,operator
      ) VALUES(?,?,?,?,?,?)`).bind(
        processId,
        String(historyRow.at ?? now),
        String(historyRow.event ?? "OUTREACH_UPDATED"),
        JSON.stringify(historyRow.fields ?? []),
        String(historyRow.status ?? raw.status ?? "NAO_INICIADO"),
        String(historyRow.operator ?? raw.operator ?? "Ana Fonseca"),
      ).run();
    }
  }

  await env.DB.prepare("DELETE FROM proposals").run();
  for (const raw of operations.proposals ?? []) {
    const value = (snake: string, camel?: string) =>
      raw[snake] ?? (camel ? raw[camel] : undefined);
    await env.DB.prepare(`INSERT INTO proposals(
      number,created_at,status,process_id,supplier,supplier_cnpj,agency,tender,
      administrative_process,decision_maker,contract_value,guarantee_percentage,
      insured_amount,annual_rate,term_months,estimated_premium,notes,operator
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(
      String(value("number") ?? ""),
      String(value("created_at", "createdAt") ?? now),
      String(value("status") ?? "GERADA"),
      String(value("process_id", "processId") ?? ""),
      String(value("supplier") ?? ""),
      String(value("supplier_cnpj", "supplierCnpj") ?? ""),
      String(value("agency") ?? ""),
      String(value("tender") ?? ""),
      String(value("administrative_process", "administrativeProcess") ?? ""),
      String(value("decision_maker", "decisionMaker") ?? ""),
      Number(value("contract_value", "contractValue") ?? 0),
      Number(value("guarantee_percentage", "guaranteePercentage") ?? 0),
      Number(value("insured_amount", "insuredAmount") ?? 0),
      Number(value("annual_rate", "annualRate") ?? 0),
      Number(value("term_months", "termMonths") ?? 0),
      Number(value("estimated_premium", "estimatedPremium") ?? 0),
      String(value("notes") ?? ""),
      String(value("operator") ?? "Ana Fonseca"),
    ).run();
  }
  for (const [key, value] of Object.entries(operations.counters ?? {})) {
    await env.DB.prepare(`INSERT INTO counters(key,value) VALUES(?,?)
      ON CONFLICT(key) DO UPDATE SET value=MAX(value,excluded.value)`)
      .bind(key, Number(value)).run();
  }
  for (const [processId, raw] of Object.entries(operations.document_jobs ?? {})) {
    const status = String(raw.status ?? "");
    const requestedAt = String(raw.requested_at ?? raw.requestedAt ?? now);
    const updatedAt = String(raw.updated_at ?? raw.updatedAt ?? now);
    await env.DB.prepare(`INSERT INTO document_jobs(
      process_id,status,requested_at,updated_at,payload_json
    ) VALUES(?,?,?,?,?)
    ON CONFLICT(process_id) DO UPDATE SET
      status=excluded.status,requested_at=excluded.requested_at,
      updated_at=excluded.updated_at,payload_json=excluded.payload_json`)
      .bind(processId, status, requestedAt, updatedAt, JSON.stringify(raw))
      .run();
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
    document_jobs: Object.keys(operations.document_jobs ?? {}).length,
  });
}
