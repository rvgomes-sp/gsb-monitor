import { getSql } from "../../../db";
import { requireAuthenticatedSession } from "../../../lib/require-session";

// SQL cru (postgres-js) — evita os prepared statements do drizzle, incompatíveis
// com o pooler de transação do Supabase.
export async function GET() {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  try {
    const sql = getSql();
    const [contacts, history, proposalRows, jobRows] = await Promise.all([
      sql`SELECT * FROM monitor.outreach ORDER BY process_id ASC`,
      sql`SELECT * FROM monitor.outreach_history ORDER BY id ASC`,
      sql`SELECT * FROM monitor.proposals ORDER BY created_at ASC`,
      sql`SELECT * FROM monitor.document_jobs ORDER BY requested_at ASC`,
    ]);
    const historyByProcess = new Map<string, Array<Record<string, unknown>>>();
    for (const entry of history) {
      const list = historyByProcess.get(entry.process_id as string) ?? [];
      list.push(entry as Record<string, unknown>);
      historyByProcess.set(entry.process_id as string, list);
    }
    return Response.json({
      version: 2,
      storage: "Supabase",
      updated_at: new Date().toISOString(),
      outreach: Object.fromEntries(
        contacts.map((r) => [
          r.process_id,
          {
            status: r.status, decision_maker: r.decision_maker, email: r.email, phone: r.phone,
            last_contact_at: r.last_contact_at, sent_at: r.sent_at, next_follow_up_at: r.next_follow_up_at,
            subject: r.subject, body: r.body, notes: r.notes, operator: r.operator,
            created_at: r.created_at, updated_at: r.updated_at,
            history: (historyByProcess.get(r.process_id as string) ?? []).map((item) => ({
              at: item.at, event: item.event, fields: JSON.parse(String(item.fields_json ?? "[]")),
              status: item.status, operator: item.operator,
            })),
          },
        ]),
      ),
      proposals: proposalRows.map((p) => ({
        number: p.number, created_at: p.created_at, status: p.status, process_id: p.process_id,
        supplier: p.supplier, supplier_cnpj: p.supplier_cnpj, agency: p.agency, tender: p.tender,
        administrative_process: p.administrative_process, decision_maker: p.decision_maker,
        contract_value: p.contract_value, guarantee_percentage: p.guarantee_percentage,
        insured_amount: p.insured_amount, annual_rate: p.annual_rate, term_months: p.term_months,
        estimated_premium: p.estimated_premium, notes: p.notes, operator: p.operator,
      })),
      document_jobs: Object.fromEntries(jobRows.map((j) => [j.process_id, JSON.parse(String(j.payload_json ?? "{}"))])),
    });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Falha no banco." },
      { status: 500 },
    );
  }
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
