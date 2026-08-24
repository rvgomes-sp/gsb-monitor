import { cookies } from "next/headers";
import { getSql } from "../../../db";
import { ensureDatabase } from "../../../db/runtime";
import {
  portalProfile,
  SESSION_COOKIE,
  verifySessionToken,
} from "../../../lib/auth";
import { requireAuthenticatedSession } from "../../../lib/require-session";

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
    const payload = await request.json() as Record<string, unknown>;
    const processId = String(payload.process_id ?? "").trim();
    const supplier = String(payload.supplier ?? "").trim();
    const contractValue = Number(payload.contract_value);
    const guaranteePercentage = Number(payload.guarantee_percentage);
    const annualRate = Number(payload.annual_rate);
    const termMonths = Number(payload.term_months);
    if (!processId || !supplier) {
      return Response.json({ error: "Processo e fornecedor são obrigatórios." }, { status: 400 });
    }
    if (![contractValue, guaranteePercentage, annualRate, termMonths].every(Number.isFinite)) {
      return Response.json({ error: "Valores da proposta inválidos." }, { status: 400 });
    }

    const now = new Date();
    const year = now.getFullYear();
    const counterKey = `proposal_${year}`;
    const sql = getSql();
    const counterRows = await sql<{ value: number }[]>`
      INSERT INTO monitor.counters(key,value) VALUES(${counterKey}, 1)
      ON CONFLICT(key) DO UPDATE SET value = monitor.counters.value + 1
      RETURNING value`;
    const number = `VF-${year}-${String(counterRows[0]?.value ?? 1).padStart(4, "0")}`;
    const insuredAmount = contractValue * guaranteePercentage / 100;
    const estimatedPremium = insuredAmount * annualRate / 100 * termMonths / 12;
    const proposal = {
      number,
      created_at: now.toISOString(),
      status: "RASCUNHO",
      process_id: processId,
      supplier,
      supplier_cnpj: String(payload.supplier_cnpj ?? ""),
      agency: String(payload.agency ?? ""),
      tender: String(payload.tender ?? ""),
      administrative_process: String(payload.administrative_process ?? ""),
      decision_maker: String(payload.decision_maker ?? ""),
      contract_value: contractValue,
      guarantee_percentage: guaranteePercentage,
      insured_amount: insuredAmount,
      annual_rate: annualRate,
      term_months: termMonths,
      estimated_premium: estimatedPremium,
      notes: String(payload.notes ?? ""),
      operator: await authenticatedOperator(payload.operator),
    };
    await sql`INSERT INTO monitor.proposals(
      number,created_at,status,process_id,supplier,supplier_cnpj,agency,tender,
      administrative_process,decision_maker,contract_value,guarantee_percentage,
      insured_amount,annual_rate,term_months,estimated_premium,notes,operator
    ) VALUES(
      ${proposal.number}, ${proposal.created_at}, ${proposal.status}, ${proposal.process_id},
      ${proposal.supplier}, ${proposal.supplier_cnpj}, ${proposal.agency}, ${proposal.tender},
      ${proposal.administrative_process}, ${proposal.decision_maker}, ${proposal.contract_value},
      ${proposal.guarantee_percentage}, ${proposal.insured_amount}, ${proposal.annual_rate},
      ${proposal.term_months}, ${proposal.estimated_premium}, ${proposal.notes}, ${proposal.operator}
    )`;
    return Response.json({ status: "OK", proposal }, { status: 201 });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Falha ao gerar proposta." },
      { status: 500 },
    );
  }
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
