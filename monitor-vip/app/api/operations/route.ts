import { asc } from "drizzle-orm";
import { getDb } from "../../../db";
import { ensureDatabase } from "../../../db/runtime";
import {
  documentJobs,
  outreach,
  outreachHistory,
  proposals,
} from "../../../db/schema";
import { requireAuthenticatedSession } from "../../../lib/require-session";

export async function GET() {
  const guard = await requireAuthenticatedSession();
  if (!guard.ok) return guard.response;
  try {
    await ensureDatabase();
    const db = getDb();
    const [contacts, history, proposalRows, jobRows] = await Promise.all([
      db.select().from(outreach).orderBy(asc(outreach.processId)),
      db.select().from(outreachHistory).orderBy(asc(outreachHistory.id)),
      db.select().from(proposals).orderBy(asc(proposals.createdAt)),
      db.select().from(documentJobs).orderBy(asc(documentJobs.requestedAt)),
    ]);
    const historyByProcess = new Map<string, typeof history>();
    for (const entry of history) {
      const list = historyByProcess.get(entry.processId) ?? [];
      list.push(entry);
      historyByProcess.set(entry.processId, list);
    }
    return Response.json({
      version: 2,
      storage: "D1",
      updated_at: new Date().toISOString(),
      outreach: Object.fromEntries(
        contacts.map((record) => [
          record.processId,
          {
            status: record.status,
            decision_maker: record.decisionMaker,
            email: record.email,
            phone: record.phone,
            last_contact_at: record.lastContactAt,
            sent_at: record.sentAt,
            next_follow_up_at: record.nextFollowUpAt,
            subject: record.subject,
            body: record.body,
            notes: record.notes,
            operator: record.operator,
            created_at: record.createdAt,
            updated_at: record.updatedAt,
            history: (historyByProcess.get(record.processId) ?? []).map((item) => ({
              at: item.at,
              event: item.event,
              fields: JSON.parse(item.fieldsJson),
              status: item.status,
              operator: item.operator,
            })),
          },
        ]),
      ),
      proposals: proposalRows.map((proposal) => ({
        number: proposal.number,
        created_at: proposal.createdAt,
        status: proposal.status,
        process_id: proposal.processId,
        supplier: proposal.supplier,
        supplier_cnpj: proposal.supplierCnpj,
        agency: proposal.agency,
        tender: proposal.tender,
        administrative_process: proposal.administrativeProcess,
        decision_maker: proposal.decisionMaker,
        contract_value: proposal.contractValue,
        guarantee_percentage: proposal.guaranteePercentage,
        insured_amount: proposal.insuredAmount,
        annual_rate: proposal.annualRate,
        term_months: proposal.termMonths,
        estimated_premium: proposal.estimatedPremium,
        notes: proposal.notes,
        operator: proposal.operator,
      })),
      document_jobs: Object.fromEntries(
        jobRows.map((job) => [
          job.processId,
          JSON.parse(job.payloadJson),
        ]),
      ),
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
