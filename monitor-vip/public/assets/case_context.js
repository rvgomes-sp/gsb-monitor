const FALLBACK_FEED = "./data/monitor_feed_real.json";
const DOSSIER_SOURCE = "./data/commercial_intelligence_cases.json";

export function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function brl(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}

export function compactBrl(value) {
  const n = Number(value) || 0;
  if (Math.abs(n) >= 1_000_000) {
    return `R$ ${(n / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MM`;
  }
  return brl(n);
}

export function queryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

export function todayYmd() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json();
}

function demoFallbackAllowed() {
  const params = new URLSearchParams(window.location.search);
  return params.get("demo") === "1" || ["localhost", "127.0.0.1"].includes(window.location.hostname);
}

async function loadFeed() {
  try {
    const feed = await getJson("./api/feed");
    return { value: feed, degraded: false, source: "API / Supabase" };
  } catch (error) {
    if (!demoFallbackAllowed()) throw error;
    const feed = await getJson(FALLBACK_FEED);
    return { value: feed, degraded: true, source: "fallback demonstrativo" };
  }
}

async function loadOperations() {
  try {
    return { value: await getJson("./api/operations"), degraded: false };
  } catch (error) {
    if (!demoFallbackAllowed()) throw error;
    return {
      value: { storage: "DEMO", outreach: {}, proposals: [], document_jobs: {} },
      degraded: true,
    };
  }
}

async function loadUser() {
  try {
    const session = await getJson("./api/auth/session");
    return session.user || session;
  } catch (error) {
    if (!demoFallbackAllowed()) throw error;
    return { name: "Usuário", role: "Demonstração", initials: "US" };
  }
}

async function loadDossiers() {
  try {
    const data = await getJson(DOSSIER_SOURCE);
    return data.cases || {};
  } catch (_) {
    return {};
  }
}

export async function loadCaseContext() {
  const [feedState, operationState, dossiers, user] = await Promise.all([
    loadFeed(),
    loadOperations(),
    loadDossiers(),
    loadUser(),
  ]);

  return {
    feed: feedState.value,
    operations: operationState.value,
    cases: dossiers,
    user,
    degraded: feedState.degraded || operationState.degraded,
    source: feedState.source,
  };
}

export function outreachFor(context, processId) {
  return context.operations?.outreach?.[processId] || null;
}

export function proposalsFor(context, processId) {
  return (context.operations?.proposals || []).filter((proposal) => proposal.process_id === processId);
}

export function dossierFor(context, processId) {
  return context.cases?.[processId] || null;
}

export function findOpportunity(context, processId) {
  return context.feed?.opportunities?.find((item) => item.processo === processId) || null;
}

export function guaranteeOf(item, dossier) {
  const percent = dossier?.guarantee?.executionPercent
    || Number(String(item?.percentual_garantia_execucao || "").replace("%", ""))
    || null;
  const contractValue = Number(item?.valor_numero || dossier?.guarantee?.contractValue || 0);
  return {
    percent,
    value: percent ? contractValue * (percent / 100) : null,
    contractValue,
    termMonths: dossier?.guarantee?.executionTermMonths || null,
  };
}

export function mainPain(item, dossier) {
  if (dossier?.documentaryReading?.clauses?.some((clause) => clause.classification === "DIVERGENCIA_DOCUMENTAL")) {
    return "Estruturação da garantia";
  }
  if (dossier?.positioning?.capacityReadiness?.level === "EXIGE_VALIDACAO_IMEDIATA") {
    return "Capacidade / limite";
  }
  if (dossier?.flags?.includes("LOGISTICA_DESAFIADORA")) {
    return "Mobilização / operação";
  }
  if (item?.garantia_execucao === "SIM") return "Garantia contratual";
  return "Em investigação";
}

export function urgencyFor(record, dossier) {
  if (record?.next_follow_up_at) {
    if (record.next_follow_up_at < todayYmd()) return "Alta";
    if (record.next_follow_up_at === todayYmd()) return "Hoje";
  }
  if (dossier?.stage === "HOMOLOGADA_AGUARDANDO_FORMALIZACAO") return "Alta";
  return "Moderada";
}

export function statusLabel(status) {
  const labels = {
    NAO_INICIADO: "Não iniciado",
    EM_PREPARACAO: "Em preparação",
    PRONTO_PARA_ENVIO: "Pronto para envio",
    ENVIADO: "Enviado",
    AGUARDANDO_RETORNO: "Aguardando retorno",
    RESPONDEU: "Respondeu",
    PROPOSTA_EM_PREPARACAO: "Proposta em preparação",
    PROPOSTA_ENVIADA: "Proposta enviada",
    NEGOCIACAO: "Negociação",
    FECHADO: "Fechado",
    SEM_INTERESSE: "Sem interesse",
  };
  return labels[status] || status || "Não iniciado";
}

export function caseIdentity(item, dossier) {
  return {
    processId: item?.processo || dossier?.processId || "",
    company: item?.fornecedor || dossier?.supplier || "Tomador",
    cnpj: item?.fornecedor_cnpj || dossier?.supplierCnpj || "",
    agency: item?.orgao || dossier?.agency || "—",
    tender: item?.abordagem?.edital || dossier?.tender || item?.processo || "—",
    object: item?.objeto || dossier?.item || "—",
    homologationAt: item?.data_homologacao || dossier?.homologationAt || "—",
    value: Number(item?.valor_numero || dossier?.guarantee?.contractValue || 0),
    valueLabel: item?.valor || compactBrl(item?.valor_numero || dossier?.guarantee?.contractValue || 0),
    route: item?.rota || dossier?.commercialRoute || "A confirmar",
  };
}
