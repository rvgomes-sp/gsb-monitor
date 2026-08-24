import {
  assertCommercialCase,
  calculateGuaranteeStack,
  interpolateDraft,
  observedPortfolioTotal,
  sortApproachMap
} from "./commercial_intelligence.mjs";

let feedData = null;
let commercialCases = {};
let operationsState = {
  outreach: {},
  proposals: [],
  counters: {},
  document_jobs: {}
};
let currentEmailOpportunity = null;
let currentOutreachOpportunity = null;
let currentInsightsOpportunity = null;
let currentProposalOpportunity = null;
let currentCommercialCase = null;
let currentProposalText = "";
let authenticatedPortalUser = null;
let activeRouteFilter = "TODAS";
let currentOpportunityPage = 1;
let lastOpportunityQuery = "";
let lastOpportunityPageSize = 0;
let lastOperationsSignature = "";
let operationalRefreshTimer = 0;

const STATUS_LABELS = {
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
  SEM_INTERESSE: "Sem interesse"
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBrl(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL"
  }).format(Number(value) || 0);
}

function localDate(value) {
  if (!value) return "—";
  const date = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: value.length === 10 ? undefined : "short"
  }).format(date);
}

function todayYmd() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now - offset).toISOString().slice(0, 10);
}

function addDaysYmd(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date - offset).toISOString().slice(0, 10);
}

async function loadFeedLegacy() {
  const response = await fetch("./data/monitor_feed_real.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Feed de oportunidades indisponível.");
  return response.json();
}

async function loadFeed() {
  const cloud = await fetch("./api/feed", { cache: "no-store" });
  if (cloud.ok) return cloud.json();
  return loadFeedLegacy();
}

async function loadOperations() {
  const response = await fetch("./api/operations", { cache: "no-store" });
  if (!response.ok) {
    return { outreach: {}, proposals: [], counters: {}, document_jobs: {}, storage: "LOCAL_FALLBACK" };
  }
  return response.json();
}

async function loadCommercialIntelligence() {
  const response = await fetch("./data/commercial_intelligence_cases.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Dossiês de inteligência comercial indisponíveis.");
  const payload = await response.json();
  return payload.cases || {};
}

async function loadPortalSession() {
  const response = await fetch("./api/auth/session", {
    cache: "no-store",
    credentials: "same-origin"
  });
  if (response.status === 401) {
    window.location.replace("/login");
    throw new Error("Sessão encerrada.");
  }
  if (!response.ok) throw new Error("Não foi possível identificar o usuário conectado.");
  const payload = await response.json();
  return payload.user;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Não foi possível salvar.");
  return data;
}

function statusClass(status) {
  if (!status) return "";
  if (status === "SIM" || status === "FECHADO" || status === "RESPONDEU") return "ready";
  if (status === "NAO" || status === "SEM_INTERESSE") return "blocked";
  if (status.includes("NAO_IDENTIFICADO")) return "review";
  if (status.includes("PENDENTE") || status.includes("AGUARDANDO")) return "review";
  if (status.includes("ENVIADO") || status.includes("NEGOCIACAO")) return "probe";
  return "";
}

function renderBrand(feed, portalUser) {
  document.querySelector("#brand-title").textContent = feed.brand.title;
  document.querySelector("#brand-subtitle").textContent = feed.brand.subtitle;
  document.querySelector("#signature-name").textContent = feed.brand.signature;
  document.querySelector("#signature-message").textContent = `"${feed.brand.message}"`;
  document.querySelector("#operator-name").textContent = portalUser?.name || "Usuário autenticado";
  document.querySelector("#operator-role").textContent = portalUser?.role || portalUser?.email || "";
  document.querySelector("#operator-initials").textContent = portalUser?.initials || "US";
}

async function logoutPortal() {
  const button = document.querySelector("#logout-button");
  button.disabled = true;
  button.innerHTML = "<span aria-hidden=\"true\">↪</span> Saindo...";

  try {
    await fetch("./api/auth/logout", {
      method: "POST",
      cache: "no-store",
      credentials: "same-origin"
    });
  } finally {
    window.location.replace("/login");
  }
}

function renderKpis(feed) {
  document.querySelector("#kpis").innerHTML = feed.kpis.map(kpi => `
    <section class="card kpi">
      <div class="icon">${escapeHtml(kpi.icon)}</div>
      <small>${escapeHtml(kpi.label)}</small>
      <strong>${escapeHtml(kpi.value)}</strong>
      <span>${escapeHtml(kpi.trend)}</span>
    </section>
  `).join("");
}

function routeFromQueue(queue) {
  if (queue.event_id === "VF") return "Vazquez";
  if (queue.event_id === "VM") return "Vieira";
  return "TODAS";
}

function scrollToOpportunities(behavior = "smooth") {
  const target = document.querySelector("#opportunities-section");
  if (!target) return;
  const top = target.getBoundingClientRect().top + window.scrollY - 18;
  window.scrollTo({ top: Math.max(0, top), left: 0, behavior });
}

function normalizeLegacyOpportunityHash() {
  if (window.location.hash !== "#opportunities-section") {
    window.scrollTo({ top: window.scrollY, left: 0, behavior: "auto" });
    return false;
  }
  window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  window.scrollTo({ top: window.scrollY, left: 0, behavior: "auto" });
  return true;
}

function selectOpportunityRoute(feed, route, behavior = "smooth") {
  activeRouteFilter = route;
  currentOpportunityPage = 1;
  renderRouteNavigation(feed);
  renderOpportunities(feed, document.querySelector("#opportunity-search").value);
  scrollToOpportunities(behavior);
}

function renderQueues(feed) {
  document.querySelector("#queues").innerHTML = feed.queues.map(queue => `
    <section class="card queue ${queue.priority === "high" ? "high" : ""}">
      <small>${escapeHtml(queue.subtitle)}</small>
      <h3>${escapeHtml(queue.event_id)}<br>${escapeHtml(queue.label)}</h3>
      <p>${escapeHtml(queue.count)} registros</p>
      <button type="button" class="btn" data-queue-route="${routeFromQueue(queue)}">${escapeHtml(queue.button)}<span>→</span></button>
    </section>
  `).join("");
  document.querySelectorAll("[data-queue-route]").forEach(button => {
    button.addEventListener("click", () => {
      selectOpportunityRoute(feed, button.dataset.queueRoute);
    });
  });
}

function renderEvents(feed) {
  document.querySelector("#events").innerHTML = feed.events.map(event => `
    <div class="event-node ${event[0] === "EVT-007" ? "active" : ""}">
      <strong>${escapeHtml(event[0])}</strong>
      <span>${escapeHtml(event[1])}</span><br>
      <span>${escapeHtml(event[2])}</span>
    </div>
  `).join("");
}

function renderInsights(feed) {
  const groups = [feed.insights.slice(0, 2), feed.insights.slice(2, 4)];
  document.querySelector("#insight-left").innerHTML = groups[0].map(insight => `
    <div class="insight"><strong>${escapeHtml(insight.name)}</strong><p>${escapeHtml(insight.desc)}</p></div>
  `).join("");
  document.querySelector("#insight-right").innerHTML = groups[1].map(insight => `
    <div class="insight"><strong>${escapeHtml(insight.name)}</strong><p>${escapeHtml(insight.desc)}</p></div>
  `).join("");
}

function renderSummary(feed) {
  document.querySelector("#summary-organs").textContent = feed.summary?.organs ?? "—";
  document.querySelector("#summary-states").textContent = feed.summary?.states ?? "—";
  document.querySelector("#summary-opportunities").textContent = feed.summary?.opportunities ?? "—";
}

function routeMetrics(feed, route) {
  const items = route === "TODAS"
    ? feed.opportunities
    : feed.opportunities.filter(item => item.rota.includes(route));
  return {
    count: items.length,
    value: items.reduce((total, item) => total + (Number(item.valor_numero) || 0), 0)
  };
}

function renderRouteNavigation(feed) {
  const routes = [
    { key: "TODAS", label: "Todas as oportunidades", short: "Visão consolidada", className: "all" },
    { key: "Vazquez", label: "Vazquez & Fonseca", short: "Corretagem · acima de R$ 10 milhões", className: "broker" },
    { key: "Vieira", label: "Vieira Mendonça", short: "Consultoria · de R$ 1 a 10 milhões", className: "consulting" }
  ];
  document.querySelector("#route-navigation").innerHTML = routes.map(route => {
    const metrics = routeMetrics(feed, route.key);
    return `
      <button class="route-navigation-card ${route.className} ${activeRouteFilter === route.key ? "active" : ""}" type="button" data-route-filter="${route.key}">
        <span>${escapeHtml(route.short)}</span>
        <strong>${escapeHtml(route.label)}</strong>
        <div><b>${metrics.count}</b> oportunidades</div>
        <small>${formatBrl(metrics.value)}</small>
      </button>
    `;
  }).join("");
  document.querySelectorAll("[data-route-filter]").forEach(button => {
    button.addEventListener("click", () => {
      selectOpportunityRoute(feed, button.dataset.routeFilter);
    });
  });
}

function outreachFor(processId) {
  return operationsState.outreach?.[processId] || { status: "NAO_INICIADO" };
}

function documentJobFor(processId) {
  return operationsState.document_jobs?.[processId] || null;
}

function followUpState(record) {
  const date = record.next_follow_up_at;
  if (!date) return { state: "none", label: "Sem repique" };
  const today = todayYmd();
  if (date < today) return { state: "overdue", label: `Vencido ${localDate(date)}` };
  if (date === today) return { state: "due", label: "Repique hoje" };
  return { state: "future", label: `Repique ${localDate(date)}` };
}

function operationCell(item) {
  const record = outreachFor(item.processo);
  const followUp = followUpState(record);
  return `
    <div class="workflow-state">
      <span class="workflow-badge ${statusClass(record.status)}">${escapeHtml(STATUS_LABELS[record.status] || record.status)}</span>
      <small class="follow-up ${followUp.state}">${escapeHtml(followUp.label)}</small>
    </div>
    <div class="row-actions">
      ${commercialCases[item.processo] ? `<button class="dossier-button" type="button" data-commercial-intelligence="${escapeHtml(item.processo)}">Dossiê</button>` : ""}
      ${item.rota.includes("Vazquez") ? `<button type="button" data-prepare-email="${escapeHtml(item.processo)}">E-mail</button>` : ""}
      <button type="button" data-manage-outreach="${escapeHtml(item.processo)}">Controle</button>
      <button type="button" data-company-insights="${escapeHtml(item.processo)}">Insights</button>
      ${item.rota.includes("Vazquez") ? `<button type="button" data-create-proposal="${escapeHtml(item.processo)}">Proposta</button>` : ""}
    </div>
  `;
}

function documentCell(item) {
  const links = (item.documentos || []).map(document => `
    <a class="document-link" href="${escapeHtml(document.url)}" target="_blank" rel="noopener">${escapeHtml(document.label)}</a>
  `).join("");
  const job = documentJobFor(item.processo);
  const isRunning = ["FILA", "PROCESSANDO"].includes(job?.status);
  const buttonLabel = isRunning
    ? (job.status === "FILA" ? "Na fila..." : "Lendo edital...")
    : (links ? "Reler elegível" : "Buscar e ler edital");
  const jobMessage = job
    ? `<small class="document-job ${String(job.status).toLowerCase()}">${escapeHtml(job.message || job.status)}</small>`
    : "";
  return `
    <div class="document-links">${links || "<span class=\"muted-document\">Ainda não baixado</span>"}</div>
    <button
      class="document-read-button"
      type="button"
      data-read-document="${escapeHtml(item.processo)}"
      ${isRunning ? "disabled" : ""}
    >${escapeHtml(buttonLabel)}</button>
    ${jobMessage}
  `;
}

function opportunityPageSize() {
  return window.matchMedia("(max-width: 1100px)").matches ? 8 : 20;
}

function renderOpportunityPagination(total, page, pageSize) {
  const container = document.querySelector("#opportunity-pagination");
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const first = total ? ((page - 1) * pageSize) + 1 : 0;
  const last = Math.min(total, page * pageSize);
  container.innerHTML = `
    <span><strong>${first}–${last}</strong> de ${total} oportunidades</span>
    <div>
      <button type="button" data-opportunity-page="${page - 1}" ${page <= 1 ? "disabled" : ""}>Anterior</button>
      <small>Página ${page} de ${totalPages}</small>
      <button type="button" data-opportunity-page="${page + 1}" ${page >= totalPages ? "disabled" : ""}>Próxima</button>
    </div>
  `;
  container.querySelectorAll("[data-opportunity-page]").forEach(button => {
    button.addEventListener("click", () => {
      currentOpportunityPage = Number(button.dataset.opportunityPage);
      renderOpportunities(feedData, lastOpportunityQuery);
      scrollToOpportunities("smooth");
    });
  });
}

function renderOpportunities(feed, query = "") {
  const normalized = query.trim().toLocaleLowerCase("pt-BR");
  const routeFiltered = activeRouteFilter === "TODAS"
    ? feed.opportunities
    : feed.opportunities.filter(item => item.rota.includes(activeRouteFilter));
  const opportunities = normalized
    ? routeFiltered.filter(item => [
        item.orgao,
        item.processo,
        item.fornecedor,
        item.fornecedor_cnpj,
        item.objeto,
        item.modalidade
      ].join(" ").toLocaleLowerCase("pt-BR").includes(normalized))
    : routeFiltered;
  const pageSize = opportunityPageSize();
  const totalPages = Math.max(1, Math.ceil(opportunities.length / pageSize));
  if (currentOpportunityPage > totalPages) currentOpportunityPage = totalPages;
  if (currentOpportunityPage < 1) currentOpportunityPage = 1;
  lastOpportunityQuery = query;
  lastOpportunityPageSize = pageSize;
  const pageStart = (currentOpportunityPage - 1) * pageSize;
  const visibleOpportunities = opportunities.slice(pageStart, pageStart + pageSize);

  document.querySelector("#opportunities").innerHTML = visibleOpportunities.map(item => {
    const guarantee = item.percentual_garantia_execucao
      ? `${item.status} · ${item.percentual_garantia_execucao}`
      : item.status;
    return `
      <tr>
        <td data-label="Tomador e item" class="opportunity-company">
          <strong>${escapeHtml(item.fornecedor || "Não informado")}</strong>
          <span>${escapeHtml(item.objeto)}</span>
          <small>${escapeHtml(item.fornecedor_cnpj || "")} · ${escapeHtml(item.porte || "")}</small>
        </td>
        <td data-label="Licitação" class="opportunity-tender">
          <strong>${escapeHtml(item.orgao)}</strong>
          <span>${escapeHtml(item.modalidade || "")}</span>
          <small>${escapeHtml(item.processo)}</small>
        </td>
        <td data-label="Homologação" class="opportunity-date">
          <strong>${escapeHtml(item.data_homologacao || "")}</strong>
          <span>${escapeHtml(item.evento)}</span>
          <small>Atualizado ${escapeHtml(item.atualizado)}</small>
        </td>
        <td data-label="Garantia e documentos" class="documents-cell">
          <span class="status ${statusClass(item.status)}">${escapeHtml(guarantee)}</span>
          ${documentCell(item)}
        </td>
        <td data-label="Valor e rota" class="opportunity-value">
          <strong>${escapeHtml(item.valor)}</strong>
          <span class="${item.rota.includes("Vazquez") ? "route-vf" : "route-vm"}">${item.rota.includes("Vazquez") ? "Corretora VF" : "Consultoria VM"}</span>
        </td>
        <td data-label="Operação" class="operations-cell">${operationCell(item)}</td>
      </tr>
    `;
  }).join("");

  bindOpportunityActions(feed);
  renderOpportunityPagination(opportunities.length, currentOpportunityPage, pageSize);
}

function operationsSignature(operations) {
  return JSON.stringify({
    outreach: operations.outreach || {},
    proposals: operations.proposals || [],
    counters: operations.counters || {},
    document_jobs: operations.document_jobs || {}
  });
}

function findOpportunity(processId) {
  return feedData?.opportunities.find(item => item.processo === processId);
}

function bindOpportunityActions(feed) {
  document.querySelectorAll("[data-prepare-email]").forEach(button => {
    button.addEventListener("click", () => openEmailComposer(findOpportunity(button.dataset.prepareEmail)));
  });
  document.querySelectorAll("[data-manage-outreach]").forEach(button => {
    button.addEventListener("click", () => openOutreach(findOpportunity(button.dataset.manageOutreach)));
  });
  document.querySelectorAll("[data-company-insights]").forEach(button => {
    button.addEventListener("click", () => openCompanyInsights(findOpportunity(button.dataset.companyInsights)));
  });
  document.querySelectorAll("[data-commercial-intelligence]").forEach(button => {
    button.addEventListener("click", () => openCommercialIntelligence(button.dataset.commercialIntelligence));
  });
  document.querySelectorAll("[data-create-proposal]").forEach(button => {
    button.addEventListener("click", () => openProposal(findOpportunity(button.dataset.createProposal)));
  });
  document.querySelectorAll("[data-read-document]").forEach(button => {
    button.addEventListener("click", () => requestDocumentReading(button.dataset.readDocument));
  });
}

async function requestDocumentReading(processId) {
  const button = document.querySelector(`[data-read-document="${CSS.escape(processId)}"]`);
  if (button) {
    button.disabled = true;
    button.textContent = "Adicionando à fila...";
  }
  try {
    const response = await postJson("./api/document-reading", {
      process_id: processId
    });
    operationsState.document_jobs ||= {};
    operationsState.document_jobs[processId] = response.job;
    renderOpportunities(feedData, document.querySelector("#opportunity-search").value);
    renderOperationalPulse();
  } catch (error) {
    if (button) {
      button.disabled = false;
      button.textContent = "Tentar novamente";
    }
    alert(`Leitura documental: ${error.message}`);
  }
}

let previousDocumentJobs = {};

async function refreshOperationalState() {
  try {
    const operations = await loadOperations();
    const nextSignature = operationsSignature(operations);
    if (nextSignature === lastOperationsSignature) return;
    const previous = previousDocumentJobs;
    operationsState = operations;
    lastOperationsSignature = nextSignature;
    const jobs = operations.document_jobs || {};
    const completedNow = Object.entries(jobs).some(([processId, job]) =>
      job.status === "CONCLUIDO" && previous[processId] !== "CONCLUIDO"
    );
    previousDocumentJobs = Object.fromEntries(
      Object.entries(jobs).map(([processId, job]) => [processId, job.status])
    );
    if (completedNow) {
      feedData = await loadFeed();
      renderKpis(feedData);
      renderQueues(feedData);
      renderSummary(feedData);
      renderRouteNavigation(feedData);
    }
    renderOpportunities(
      feedData,
      document.querySelector("#opportunity-search").value
    );
    renderOperationalPulse();
  } catch (error) {
    console.warn("Atualização operacional temporariamente indisponível.", error);
  }
}

function scheduleOperationalRefresh(delay = 5000) {
  clearTimeout(operationalRefreshTimer);
  operationalRefreshTimer = window.setTimeout(async () => {
    await refreshOperationalState();
    scheduleOperationalRefresh(
      operationsState.storage === "LOCAL_FALLBACK" ? 30000 : 5000
    );
  }, delay);
}

function operationalMetrics() {
  const records = Object.values(operationsState.outreach || {});
  const vfProcessIds = new Set(
    (feedData?.opportunities || [])
      .filter(item => item.rota.includes("Vazquez"))
      .map(item => item.processo)
  );
  const vfRecords = records.filter(record => vfProcessIds.has(record.process_id));
  const today = todayYmd();
  const due = records.filter(record => record.next_follow_up_at === today).length;
  const overdue = records.filter(record =>
    record.next_follow_up_at &&
    record.next_follow_up_at < today &&
    !["FECHADO", "SEM_INTERESSE"].includes(record.status)
  ).length;
  const onTrack = records.filter(record =>
    !["NAO_INICIADO", "FECHADO", "SEM_INTERESSE"].includes(record.status) &&
    (!record.next_follow_up_at || record.next_follow_up_at > today)
  ).length;
  const vfTotal = vfProcessIds.size;
  const toPrepare = Math.max(0, vfTotal - vfRecords.filter(record => record.status !== "NAO_INICIADO").length);
  const waiting = records.filter(record => ["ENVIADO", "AGUARDANDO_RETORNO"].includes(record.status)).length;
  const negotiations = records.filter(record => ["RESPONDEU", "NEGOCIACAO", "PROPOSTA_ENVIADA"].includes(record.status)).length;
  return { due, overdue, onTrack, toPrepare, waiting, negotiations };
}

function renderOperationalPulse() {
  const metrics = operationalMetrics();
  document.querySelector("#signal-on-track").textContent = metrics.onTrack;
  document.querySelector("#signal-due").textContent = metrics.due;
  document.querySelector("#signal-overdue").textContent = metrics.overdue;
  document.querySelector("#ops-to-prepare").textContent = metrics.toPrepare;
  document.querySelector("#ops-waiting").textContent = metrics.waiting;
  document.querySelector("#ops-proposals").textContent = operationsState.proposals?.length || 0;
  document.querySelector("#ops-negotiations").textContent = metrics.negotiations;

  const messages = [
    metrics.overdue ? `${metrics.overdue} repique(s) vencido(s) pedem ação imediata.` : "Nenhum repique vencido neste momento.",
    metrics.due ? `${metrics.due} contato(s) programado(s) para hoje.` : "Agenda de repiques de hoje está livre.",
    "Cada homologação é o início de um relacionamento, não o fim da licitação.",
    "Limite, subscrição, emissão, vigência e aditivos: acompanhamento de ponta a ponta.",
    "Inteligência que protege. Dados que decidem. Oportunidades que transformam."
  ];
  const track = document.querySelector("#ticker-track");
  track.textContent = `${messages.join("   ◆   ")}   ◆   ${messages.join("   ◆   ")}`;
}

function startClock() {
  const update = () => {
    const now = new Date();
    document.querySelector("#live-date").textContent = new Intl.DateTimeFormat("pt-BR", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric"
    }).format(now);
    document.querySelector("#live-time").textContent = now.toLocaleTimeString("pt-BR");
  };
  update();
  setInterval(update, 1000);
}

function guaranteeParagraph(item) {
  if (item.garantia_execucao === "SIM") {
    const percentage = item.percentual_garantia_execucao || "conforme o instrumento convocatório";
    const insurance = item.seguro_garantia_execucao === "SIM"
      ? "O instrumento admite sua prestação na modalidade seguro-garantia."
      : "Nossa equipe pode confirmar as modalidades admitidas durante a estruturação.";
    return `O instrumento prevê garantia de execução de ${percentage} do valor contratual. ${insurance}`;
  }
  return "Na leitura documental realizada até o momento, a exigência de garantia de execução não foi identificada de forma conclusiva. Nossa equipe permanece acompanhando a formalização e as alterações do contrato para validar eventual necessidade de garantia.";
}

function buildEmail(item, decisionMaker) {
  const recipient = decisionMaker.trim() || "[NOME DO DECISOR]";
  const tender = item.abordagem?.edital || item.modalidade || "licitação monitorada";
  const administrativeProcess = item.abordagem?.processo_administrativo || item.processo;
  const subject = `Homologação — ${tender} | ${item.fornecedor}`;
  const body = `Prezado(a) ${recipient},

Meu nome é Ana Fonseca, Diretora Institucional da Vazquez & Fonseca.

Por meio do nosso modelo de acompanhamento contínuo das contratações públicas, acompanhamos todas as fases das licitações e identificamos a homologação do ${tender}, Processo Administrativo ${administrativeProcess}, sob controle PNCP ${item.processo}, em favor da ${item.fornecedor}, no valor de ${item.valor}.

${guaranteeParagraph(item)}

A Vazquez & Fonseca atua na estruturação completa do Seguro Garantia, incluindo:

• concessão e gestão de limite junto às seguradoras;
• apoio técnico na subscrição dos riscos da operação;
• estruturação, cotação e emissão das apólices;
• acompanhamento durante toda a vigência contratual;
• atuação nas renovações, prorrogações e, principalmente, nos potenciais aditivos que alterem valor, prazo ou obrigação garantida.

Nosso objetivo é antecipar as necessidades da contratação e manter a garantia adequada em cada etapa, reduzindo riscos operacionais e evitando urgências na emissão ou alteração das apólices.

Gostaria de confirmar se este tema está sob sua responsabilidade ou, se possível, com quem poderíamos tratar da estruturação e do acompanhamento da garantia desta contratação.

Permaneço à disposição.

Atenciosamente,

Ana Fonseca
Diretora Institucional
Vazquez & Fonseca`;
  return { subject, body, tender, administrativeProcess };
}

function renderEmailDraft() {
  if (!currentEmailOpportunity) return;
  const draft = buildEmail(
    currentEmailOpportunity,
    document.querySelector("#email-decision-maker").value
  );
  document.querySelector("#email-subject").value = draft.subject;
  document.querySelector("#email-body").value = draft.body;
  document.querySelector("#email-context").innerHTML = `
    <strong>${escapeHtml(draft.tender)}</strong>
    <span>${escapeHtml(currentEmailOpportunity.fornecedor)}</span>
    <span>${escapeHtml(currentEmailOpportunity.valor)}</span>
  `;
}

function openEmailComposer(item) {
  if (!item) return;
  currentEmailOpportunity = item;
  const record = outreachFor(item.processo);
  document.querySelector("#email-decision-maker").value = record.decision_maker || "";
  document.querySelector("#email-recipient").value = record.email || "";
  document.querySelector("#copy-feedback").textContent = "";
  renderEmailDraft();
  showModal("#email-modal");
  document.querySelector("#email-decision-maker").focus();
}

function closeEmailComposer() {
  hideModal("#email-modal");
  currentEmailOpportunity = null;
}

async function saveOutreach(processId, data) {
  const response = await postJson("./api/outreach", {
    process_id: processId,
    data: {
      ...data,
      operator: authenticatedPortalUser?.name || "Usuário autenticado"
    }
  });
  operationsState.outreach[processId] = response.record;
  renderOperationalPulse();
  renderOpportunities(feedData, document.querySelector("#opportunity-search").value);
  return response.record;
}

async function persistCurrentEmail(status) {
  if (!currentEmailOpportunity) return;
  return saveOutreach(currentEmailOpportunity.processo, {
    status,
    decision_maker: document.querySelector("#email-decision-maker").value,
    email: document.querySelector("#email-recipient").value,
    subject: document.querySelector("#email-subject").value,
    body: document.querySelector("#email-body").value
  });
}

async function copyText(text, successMessage, target = "#copy-feedback") {
  let copied = false;
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
    } catch (error) {
      console.warn("Clipboard API indisponível; usando cópia compatível.", error);
    }
  }
  if (!copied) {
    const helper = document.createElement("textarea");
    helper.value = text;
    helper.setAttribute("readonly", "");
    helper.className = "clipboard-helper";
    document.body.appendChild(helper);
    helper.select();
    copied = document.execCommand("copy");
    helper.remove();
  }
  document.querySelector(target).textContent = copied
    ? successMessage
    : "Não foi possível copiar automaticamente. Selecione o texto e use Ctrl+C.";
}

function openOutreach(item) {
  if (!item) return;
  currentOutreachOpportunity = item;
  const record = outreachFor(item.processo);
  document.querySelector("#outreach-context").innerHTML = `
    <strong>${escapeHtml(item.fornecedor)}</strong>
    <span>${escapeHtml(item.processo)}</span>
    <span>${escapeHtml(item.valor)}</span>
  `;
  document.querySelector("#outreach-status").value = record.status || "NAO_INICIADO";
  document.querySelector("#outreach-follow-up").value = record.next_follow_up_at || "";
  document.querySelector("#outreach-decision-maker").value = record.decision_maker || "";
  document.querySelector("#outreach-email").value = record.email || "";
  document.querySelector("#outreach-phone").value = record.phone || "";
  document.querySelector("#outreach-last-contact").value = (record.last_contact_at || "").slice(0, 16);
  document.querySelector("#outreach-notes").value = record.notes || "";
  document.querySelector("#outreach-feedback").textContent = "";
  showModal("#outreach-modal");
}

function closeOutreach() {
  hideModal("#outreach-modal");
  currentOutreachOpportunity = null;
}

async function submitOutreach() {
  if (!currentOutreachOpportunity) return;
  const feedback = document.querySelector("#outreach-feedback");
  feedback.textContent = "Salvando...";
  try {
    await saveOutreach(currentOutreachOpportunity.processo, {
      status: document.querySelector("#outreach-status").value,
      next_follow_up_at: document.querySelector("#outreach-follow-up").value,
      decision_maker: document.querySelector("#outreach-decision-maker").value,
      email: document.querySelector("#outreach-email").value,
      phone: document.querySelector("#outreach-phone").value,
      last_contact_at: document.querySelector("#outreach-last-contact").value,
      notes: document.querySelector("#outreach-notes").value
    });
    feedback.textContent = "Controle salvo e compartilhado na rede.";
  } catch (error) {
    feedback.textContent = error.message;
  }
}

function openCompanyInsights(item) {
  if (!item) return;
  currentInsightsOpportunity = item;
  const insights = item.insights_empresa || {};
  const record = outreachFor(item.processo);
  const followUp = followUpState(record);
  document.querySelector("#insights-title").textContent = item.fornecedor;
  document.querySelector("#company-insights").innerHTML = `
    <div class="insight-hero">
      <strong>${escapeHtml(item.fornecedor)}</strong>
      <span>${escapeHtml(item.fornecedor_cnpj)}</span>
      <p>${escapeHtml(item.natureza_juridica || "Natureza jurídica não informada")} · ${escapeHtml(item.porte || "Porte não informado")}</p>
    </div>
    <div class="insight-metrics">
      <div class="insight-metric"><small>Oportunidades na janela</small><strong>${escapeHtml(insights.oportunidades_na_base || 0)}</strong></div>
      <div class="insight-metric"><small>Valor homologado na janela</small><strong>${escapeHtml(insights.valor_total_na_base || "R$ 0,00")}</strong></div>
      <div class="insight-metric"><small>Maior homologação</small><strong>${escapeHtml(insights.maior_homologacao || "R$ 0,00")}</strong></div>
      <div class="insight-metric"><small>Órgãos distintos</small><strong>${escapeHtml(insights.orgaos_na_base || 0)}</strong></div>
      <div class="insight-metric"><small>UFs observadas</small><strong>${escapeHtml(insights.ufs_na_base || 0)}</strong></div>
      <div class="insight-metric"><small>Situação comercial</small><strong>${escapeHtml(STATUS_LABELS[record.status] || "Não iniciado")}</strong></div>
    </div>
    <div class="insight-notes">
      <h3>Leitura desta oportunidade</h3>
      <p><b>Órgão:</b> ${escapeHtml(item.orgao)}</p>
      <p><b>Objeto:</b> ${escapeHtml(item.objeto)}</p>
      <p><b>Garantia de execução:</b> ${escapeHtml(item.status)} ${escapeHtml(item.percentual_garantia_execucao || "")}</p>
      <p><b>Próxima ação:</b> ${escapeHtml(followUp.label)}</p>
      <p class="insight-note">Insights calculados exclusivamente sobre ${escapeHtml(insights.escopo || "a base atualmente monitorada")}; não representam todo o histórico da empresa.</p>
    </div>
  `;
  showModal("#insights-modal");
}

function closeCompanyInsights() {
  hideModal("#insights-modal");
  currentInsightsOpportunity = null;
}

function dossierStatusLabel(value) {
  const labels = {
    NAO_VERIFICADO: "Não verificado",
    VALIDACAO_HUMANA_OBRIGATORIA: "Validação humana obrigatória",
    HOMOLOGADA_AGUARDANDO_FORMALIZACAO: "Homologada · aguardando formalização",
    NAO_CONFIRMADO: "Não confirmado",
    ALTA: "Alta",
    EXIGE_VALIDACAO_IMEDIATA: "Validar imediatamente"
  };
  return labels[value] || String(value || "").replaceAll("_", " ");
}

function commercialDraftValues(caseData, draft) {
  const firstContact = sortApproachMap(caseData.approachMap || [])
    .find(contact => contact.decisionMaker && !contact.decisionMaker.startsWith("Nome a validar"));
  return {
    decisor: firstContact?.decisionMaker || "NOME DO DECISOR",
    empresa: caseData.supplier,
    edital: caseData.tender,
    processo: caseData.administrativeProcess,
    area: draft.audience
  };
}

function renderCommercialDraft(caseData, draftId) {
  const draft = (caseData.emailDrafts || []).find(item => item.id === draftId) || caseData.emailDrafts?.[0];
  if (!draft) return;
  document.querySelectorAll("[data-dossier-draft]").forEach(button => {
    button.classList.toggle("active", button.dataset.dossierDraft === draft.id);
  });
  document.querySelector("#dossier-email-audience").textContent = draft.audience;
  document.querySelector("#dossier-email-subject").value = interpolateDraft(
    draft.subject,
    commercialDraftValues(caseData, draft)
  );
  document.querySelector("#dossier-email-body").value = interpolateDraft(
    draft.body,
    commercialDraftValues(caseData, draft)
  );
  document.querySelector("#commercial-intelligence-feedback").textContent = "";
}

function bindCommercialIntelligenceActions(caseData) {
  document.querySelectorAll("[data-dossier-draft]").forEach(button => {
    button.addEventListener("click", () => renderCommercialDraft(caseData, button.dataset.dossierDraft));
  });
  document.querySelector("#copy-dossier-email").addEventListener("click", () => {
    const subject = document.querySelector("#dossier-email-subject").value;
    const body = document.querySelector("#dossier-email-body").value;
    copyText(`${subject}\n\n${body}`, "Assunto e mensagem copiados.", "#commercial-intelligence-feedback");
  });
  document.querySelector("#open-dossier-mail-client").addEventListener("click", () => {
    const subject = encodeURIComponent(document.querySelector("#dossier-email-subject").value);
    const body = encodeURIComponent(document.querySelector("#dossier-email-body").value);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  });
  document.querySelector("#send-dossier-to-composer").addEventListener("click", () => {
    const item = findOpportunity(caseData.processId);
    const subject = document.querySelector("#dossier-email-subject").value;
    const body = document.querySelector("#dossier-email-body").value;
    closeCommercialIntelligence();
    openEmailComposer(item);
    document.querySelector("#email-subject").value = subject;
    document.querySelector("#email-body").value = body;
  });
}

function openCommercialIntelligence(processId) {
  const caseData = commercialCases[processId];
  if (!caseData) return;
  assertCommercialCase(caseData);
  currentCommercialCase = caseData;
  const guarantee = calculateGuaranteeStack(caseData.guarantee);
  const contracts = caseData.portfolio?.contracts || [];
  const portfolioTotal = observedPortfolioTotal(contracts);
  const grossObserved = portfolioTotal + Number(caseData.portfolio?.newHomologationValue || 0);
  const approaches = sortApproachMap(caseData.approachMap || []);
  const documentaryFlags = (caseData.documentaryReading?.clauses || [])
    .filter(clause => clause.classification === "DIVERGENCIA_DOCUMENTAL");

  document.querySelector("#commercial-intelligence-title").textContent = caseData.caseName;
  document.querySelector("#commercial-intelligence-content").innerHTML = `
    <section class="dossier-hero">
      <div>
        <p class="dossier-kicker">EVT-007 · inteligência acionável</p>
        <h3>${escapeHtml(caseData.supplier)}</h3>
        <p>${escapeHtml(caseData.tender)} · ${escapeHtml(caseData.item)}</p>
        <div class="dossier-badges">
          <span class="dossier-badge success">Homologada em ${escapeHtml(caseData.homologationAt)}</span>
          <span class="dossier-badge danger">Divergência documental</span>
          <span class="dossier-badge warning">Limite ${escapeHtml(dossierStatusLabel(caseData.limitStatus).toLowerCase())}</span>
        </div>
      </div>
      <div class="dossier-hero-value">
        <small>Valor homologado</small>
        <strong>${formatBrl(caseData.guarantee.contractValue)}</strong>
        <span>${escapeHtml(caseData.commercialRoute)}</span>
      </div>
    </section>

    <section class="dossier-metrics">
      <article><small>Garantia principal · 10%</small><strong>${formatBrl(guarantee.executionAmount)}</strong><span>TR 4.16</span></article>
      <article><small>Cenário mínimo · 15%</small><strong>${formatBrl(guarantee.minimumNominalCapacity)}</strong><span>10% + cobertura de 5%</span></article>
      <article><small>Cenário máximo · 20%</small><strong>${formatBrl(guarantee.maximumNominalCapacity)}</strong><span>10% + cobertura de 10%</span></article>
      <article><small>Adicional art. 59</small><strong>${formatBrl(guarantee.article59Additional)}</strong><span>Não aplicável · proposta acima de 85%</span></article>
    </section>

    <section class="dossier-alert">
      <div class="dossier-alert-icon">!</div>
      <div>
        <strong>O motor encontrou uma diferença de ${formatBrl(guarantee.laborMaxAmount - guarantee.laborMinAmount)} na cobertura adicional.</strong>
        <p>${escapeHtml(caseData.documentaryReading.decision)}</p>
        <small>${documentaryFlags.map(flag => `${escapeHtml(flag.reference)}: ${escapeHtml(flag.finding)}`).join(" · ")}</small>
      </div>
    </section>

    <section class="dossier-section">
      <header><div><small>Leitura de subscrição</small><h3>Capacidade e pressão indicativa de taxa</h3></div><span class="human-review">Não é cotação nem aprovação de limite</span></header>
      <div class="dossier-two-columns">
        <article class="position-card">
          <span class="position-level warning">${escapeHtml(caseData.positioning.capacityReadiness.label)}</span>
          <p>${escapeHtml(caseData.positioning.capacityReadiness.explanation)}</p>
          <dl>
            <div><dt>Limite disponível</dt><dd>Não verificado</dd></div>
            <div><dt>Necessidade nominal</dt><dd>${guarantee.minimumTotalPercent}% a ${guarantee.maximumTotalPercent}%</dd></div>
            <div><dt>Prazo de risco</dt><dd>${caseData.guarantee.executionTermMonths} meses + ${caseData.guarantee.additionalValidityDays} dias</dd></div>
          </dl>
        </article>
        <article class="position-card">
          <span class="position-level danger">${escapeHtml(caseData.positioning.ratePressure.label)}</span>
          <div class="factor-columns">
            <div><strong>Fatores positivos</strong><ul>${caseData.positioning.ratePressure.positiveFactors.map(factor => `<li>${escapeHtml(factor)}</li>`).join("")}</ul></div>
            <div><strong>Pressões</strong><ul>${caseData.positioning.ratePressure.pressureFactors.map(factor => `<li>${escapeHtml(factor)}</li>`).join("")}</ul></div>
          </div>
          <p class="method-note">${escapeHtml(caseData.positioning.ratePressure.disclaimer)}</p>
        </article>
      </div>
    </section>

    <section class="dossier-section">
      <header><div><small>Ordem sugerida</small><h3>Mapa de abordagem</h3></div><span>${approaches.length} portas de entrada</span></header>
      <div class="approach-grid">
        ${approaches.map(contact => `
          <article class="approach-card">
            <div class="approach-priority">${contact.priority}</div>
            <div>
              <small>${escapeHtml(contact.primaryChannel)} · confiança ${escapeHtml(contact.confidence)}</small>
              <h4>${escapeHtml(contact.area)}</h4>
              <strong>${escapeHtml(contact.decisionMaker)}</strong>
              <p>${escapeHtml(contact.why)}</p>
              <span><b>Objetivo:</b> ${escapeHtml(contact.objective)}</span>
            </div>
          </article>
        `).join("")}
      </div>
    </section>

    <section class="dossier-section">
      <header>
        <div><small>Fonte pública consultada</small><h3>Carteira contratada observada</h3></div>
        <div class="portfolio-total"><small>7 contratos</small><strong>${formatBrl(portfolioTotal)}</strong></div>
      </header>
      <p class="method-note">${escapeHtml(caseData.portfolio.scope)}</p>
      <div class="dossier-table-wrap">
        <table class="dossier-table">
          <thead><tr><th>Contrato</th><th>Assinatura</th><th>Fim informado</th><th>Valor contratado</th><th>Leitura</th></tr></thead>
          <tbody>${contracts.map(contract => `
            <tr>
              <td><strong>${escapeHtml(contract.number)}</strong></td>
              <td>${escapeHtml(contract.signedAt)}</td>
              <td>${escapeHtml(contract.endAt)}</td>
              <td>${formatBrl(contract.value)}</td>
              <td><span class="portfolio-status">${escapeHtml(dossierStatusLabel(contract.status))}</span></td>
            </tr>
          `).join("")}</tbody>
        </table>
      </div>
      <div class="portfolio-summary">
        <div><small>Carteira pública observada</small><strong>${formatBrl(portfolioTotal)}</strong></div>
        <span>+</span>
        <div><small>Nova homologação</small><strong>${formatBrl(caseData.portfolio.newHomologationValue)}</strong></div>
        <span>=</span>
        <div><small>Exposição pública bruta observada</small><strong>${formatBrl(grossObserved)}</strong></div>
      </div>
      <p class="dossier-caution"><b>Não chamar de backlog:</b> faltam saldos a executar, medições, aditivos, participações em consórcio e limites já comprometidos.</p>
    </section>

    <section class="dossier-section">
      <header><div><small>Próximos dez dias</small><h3>Cadência recomendada</h3></div></header>
      <div class="cadence-track">
        ${caseData.cadence.map(step => `<article><strong>${escapeHtml(step.day)}</strong><span>${escapeHtml(step.action)}</span><small>${escapeHtml(step.goal)}</small></article>`).join("")}
      </div>
    </section>

    <section class="dossier-section email-lab">
      <header><div><small>Abordagem pronta para Ana</small><h3>E-mails arrojados e editáveis</h3></div><span id="dossier-email-audience"></span></header>
      <div class="draft-tabs">
        ${caseData.emailDrafts.map(draft => `<button type="button" data-dossier-draft="${escapeHtml(draft.id)}">${escapeHtml(draft.audience)}</button>`).join("")}
      </div>
      <label class="field"><span>Assunto</span><input id="dossier-email-subject" type="text"></label>
      <label class="field"><span>Mensagem</span><textarea id="dossier-email-body" rows="16"></textarea></label>
      <div class="email-actions">
        <button class="secondary-button" id="copy-dossier-email" type="button">Copiar assunto e mensagem</button>
        <button class="secondary-button" id="open-dossier-mail-client" type="button">Abrir no e-mail</button>
        <button class="primary-button" id="send-dossier-to-composer" type="button">Levar ao controle comercial</button>
      </div>
    </section>

    <section class="dossier-section">
      <header><div><small>Rastreabilidade</small><h3>Fontes e confiança</h3></div></header>
      <div class="evidence-list">
        ${caseData.evidence.map(evidence => `<article><span>${escapeHtml(evidence.confidence)}</span><strong>${escapeHtml(evidence.source)}</strong><p>${escapeHtml(evidence.fact)}</p></article>`).join("")}
      </div>
      <p class="method-note">Histórico de mercado: ${escapeHtml(caseData.positioning.marketHistory)} ${escapeHtml(caseData.positioning.governanceEvidence)}</p>
    </section>
  `;

  bindCommercialIntelligenceActions(caseData);
  renderCommercialDraft(caseData, caseData.emailDrafts?.[0]?.id);
  showModal("#commercial-intelligence-modal");
}

function closeCommercialIntelligence() {
  hideModal("#commercial-intelligence-modal");
  currentCommercialCase = null;
}

function parsedGuarantee(item) {
  const match = String(item.percentual_garantia_execucao || "").match(/\d+(?:[,.]\d+)?/);
  return match ? Number(match[0].replace(",", ".")) : 0;
}

function proposalEstimate() {
  const contractValue = Number(document.querySelector("#proposal-contract-value").value) || 0;
  const guarantee = Number(document.querySelector("#proposal-guarantee").value) || 0;
  const rate = Number(document.querySelector("#proposal-rate").value) || 0;
  const term = Number(document.querySelector("#proposal-term").value) || 0;
  const insured = contractValue * guarantee / 100;
  const premium = insured * rate / 100 * term / 12;
  document.querySelector("#proposal-estimate").innerHTML = `
    <div><small>Importância segurada estimada</small><strong>${formatBrl(insured)}</strong></div>
    <div><small>Prêmio estimado</small><strong>${formatBrl(premium)}</strong></div>
  `;
  return { contractValue, guarantee, rate, term, insured, premium };
}

function openProposal(item) {
  if (!item) return;
  currentProposalOpportunity = item;
  currentProposalText = "";
  const record = outreachFor(item.processo);
  document.querySelector("#proposal-context").innerHTML = `
    <strong>${escapeHtml(item.fornecedor)}</strong>
    <span>${escapeHtml(item.abordagem?.edital || item.modalidade)}</span>
    <span>${escapeHtml(item.processo)}</span>
  `;
  document.querySelector("#proposal-contract-value").value = item.valor_numero || "";
  document.querySelector("#proposal-guarantee").value = parsedGuarantee(item) || "";
  document.querySelector("#proposal-rate").value = "0.75";
  document.querySelector("#proposal-term").value = "12";
  document.querySelector("#proposal-decision-maker").value = record.decision_maker || "";
  document.querySelector("#proposal-notes").value = "";
  document.querySelector("#proposal-feedback").textContent = parsedGuarantee(item)
    ? ""
    : "Informe o percentual somente após confirmar a garantia de execução no instrumento contratual.";
  document.querySelector("#proposal-output").hidden = true;
  proposalEstimate();
  showModal("#proposal-modal");
}

function closeProposal() {
  hideModal("#proposal-modal");
  currentProposalOpportunity = null;
}

function proposalText(proposal) {
  return `PROPOSTA COMERCIAL ${proposal.number}
Vazquez & Fonseca

Destinatário: ${proposal.supplier}
Decisor: ${proposal.decision_maker || "A definir"}
Referência: ${proposal.tender}
Processo: ${proposal.administrative_process || proposal.process_id}

OBJETO
Estruturação e acompanhamento do Seguro Garantia para a contratação monitorada.

DADOS DA OPERAÇÃO
Valor da contratação: ${formatBrl(proposal.contract_value)}
Percentual da garantia: ${proposal.guarantee_percentage}%
Importância segurada estimada: ${formatBrl(proposal.insured_amount)}
Taxa anual referencial: ${proposal.annual_rate}%
Prazo considerado: ${proposal.term_months} meses
Prêmio estimado: ${formatBrl(proposal.estimated_premium)}

ESCOPO DE ATUAÇÃO
• concessão e gestão de limite;
• apoio técnico na subscrição dos riscos;
• estruturação, cotação e emissão da apólice;
• acompanhamento durante toda a vigência;
• suporte em renovações, prorrogações e potenciais aditivos.

Observações: ${proposal.notes || "Valores sujeitos à análise e aceitação das seguradoras."}

Ana Fonseca
Diretora Institucional
Vazquez & Fonseca`;
}

async function generateProposal() {
  if (!currentProposalOpportunity) return;
  const estimate = proposalEstimate();
  const feedback = document.querySelector("#proposal-feedback");
  if (!estimate.contractValue || !estimate.guarantee || !estimate.rate || !estimate.term) {
    feedback.textContent = "Preencha valor, percentual, taxa e prazo antes de gerar.";
    return;
  }
  feedback.textContent = "Gerando numeração...";
  try {
    const response = await postJson("./api/proposals", {
      process_id: currentProposalOpportunity.processo,
      supplier: currentProposalOpportunity.fornecedor,
      supplier_cnpj: currentProposalOpportunity.fornecedor_cnpj,
      agency: currentProposalOpportunity.orgao,
      tender: currentProposalOpportunity.abordagem?.edital || currentProposalOpportunity.modalidade,
      administrative_process: currentProposalOpportunity.abordagem?.processo_administrativo || currentProposalOpportunity.processo,
      decision_maker: document.querySelector("#proposal-decision-maker").value,
      contract_value: estimate.contractValue,
      guarantee_percentage: estimate.guarantee,
      annual_rate: estimate.rate,
      term_months: estimate.term,
      notes: document.querySelector("#proposal-notes").value,
      operator: authenticatedPortalUser?.name || "Usuário autenticado"
    });
    const proposal = response.proposal;
    operationsState.proposals.push(proposal);
    currentProposalText = proposalText(proposal);
    document.querySelector("#proposal-print-content").innerHTML = `
      <div class="proposal-letter">
        <small>Vazquez & Fonseca</small>
        <h1>${escapeHtml(proposal.number)}</h1>
        <h2>Estruturação e acompanhamento do Seguro Garantia</h2>
        <p><b>Destinatário:</b> ${escapeHtml(proposal.supplier)}</p>
        <p><b>Decisor:</b> ${escapeHtml(proposal.decision_maker || "A definir")}</p>
        <p><b>Referência:</b> ${escapeHtml(proposal.tender)}</p>
        <div class="proposal-numbers">
          <div><span>Valor da contratação</span><strong>${formatBrl(proposal.contract_value)}</strong></div>
          <div><span>Garantia</span><strong>${escapeHtml(proposal.guarantee_percentage)}%</strong></div>
          <div><span>Importância segurada</span><strong>${formatBrl(proposal.insured_amount)}</strong></div>
          <div><span>Prêmio estimado</span><strong>${formatBrl(proposal.estimated_premium)}</strong></div>
        </div>
        <h3>Escopo de atuação</h3>
        <p>Concessão e gestão de limite; apoio técnico na subscrição; estruturação, cotação e emissão; acompanhamento durante toda a vigência; suporte em renovações, prorrogações e potenciais aditivos.</p>
        <p><b>Observações:</b> ${escapeHtml(proposal.notes || "Valores sujeitos à análise e aceitação das seguradoras.")}</p>
        <footer>Ana Fonseca · Diretora Institucional · Vazquez & Fonseca</footer>
      </div>
    `;
    document.querySelector("#proposal-output").hidden = false;
    feedback.textContent = `${proposal.number} gerada e registrada.`;
    await saveOutreach(currentProposalOpportunity.processo, {
      status: "PROPOSTA_EM_PREPARACAO",
      decision_maker: proposal.decision_maker,
      notes: document.querySelector("#proposal-notes").value
    });
    renderOperationalPulse();
  } catch (error) {
    feedback.textContent = error.message;
  }
}

function showModal(selector) {
  document.querySelector(selector).hidden = false;
  document.body.classList.add("modal-open");
}

function hideModal(selector) {
  document.querySelector(selector).hidden = true;
  if (![...document.querySelectorAll(".email-modal, .portal-modal")].some(modal => !modal.hidden)) {
    document.body.classList.remove("modal-open");
  }
}

document.querySelector("#opportunity-search").addEventListener("input", event => {
  currentOpportunityPage = 1;
  if (feedData) renderOpportunities(feedData, event.target.value);
});
document.querySelector("#logout-button").addEventListener("click", logoutPortal);
document.querySelectorAll("[data-close-email-modal]").forEach(button => button.addEventListener("click", closeEmailComposer));
document.querySelectorAll("[data-close-outreach]").forEach(button => button.addEventListener("click", closeOutreach));
document.querySelectorAll("[data-close-insights]").forEach(button => button.addEventListener("click", closeCompanyInsights));
document.querySelectorAll("[data-close-commercial-intelligence]").forEach(button => button.addEventListener("click", closeCommercialIntelligence));
document.querySelectorAll("[data-close-proposal]").forEach(button => button.addEventListener("click", closeProposal));
document.querySelector("#print-commercial-intelligence").addEventListener("click", () => window.print());
document.querySelector("#regenerate-email").addEventListener("click", renderEmailDraft);
document.querySelector("#copy-subject").addEventListener("click", () => {
  copyText(document.querySelector("#email-subject").value, "Assunto copiado.");
});
document.querySelector("#copy-email").addEventListener("click", async () => {
  await persistCurrentEmail("EM_PREPARACAO");
  copyText(document.querySelector("#email-body").value, "Mensagem copiada. Já pode colar no e-mail.");
});
document.querySelector("#open-mail-client").addEventListener("click", async () => {
  await persistCurrentEmail("PRONTO_PARA_ENVIO");
  const recipient = document.querySelector("#email-recipient").value;
  const subject = encodeURIComponent(document.querySelector("#email-subject").value);
  const body = encodeURIComponent(document.querySelector("#email-body").value);
  window.location.href = `mailto:${encodeURIComponent(recipient)}?subject=${subject}&body=${body}`;
});
document.querySelector("#register-sent").addEventListener("click", async () => {
  if (!currentEmailOpportunity) return;
  try {
    await saveOutreach(currentEmailOpportunity.processo, {
      status: "ENVIADO",
      decision_maker: document.querySelector("#email-decision-maker").value,
      email: document.querySelector("#email-recipient").value,
      subject: document.querySelector("#email-subject").value,
      body: document.querySelector("#email-body").value,
      last_contact_at: new Date().toISOString(),
      next_follow_up_at: addDaysYmd(3)
    });
    document.querySelector("#copy-feedback").textContent = "Envio registrado. Repique agendado para 3 dias.";
  } catch (error) {
    document.querySelector("#copy-feedback").textContent = error.message;
  }
});
document.querySelector("#save-outreach").addEventListener("click", submitOutreach);
["proposal-contract-value", "proposal-guarantee", "proposal-rate", "proposal-term"].forEach(id => {
  document.querySelector(`#${id}`).addEventListener("input", proposalEstimate);
});
document.querySelector("#generate-proposal").addEventListener("click", generateProposal);
document.querySelector("#copy-proposal").addEventListener("click", () => {
  copyText(currentProposalText, "Proposta copiada.", "#proposal-feedback");
});
document.querySelector("#print-proposal").addEventListener("click", () => window.print());
document.addEventListener("keydown", event => {
  if (event.key !== "Escape") return;
  if (!document.querySelector("#email-modal").hidden) closeEmailComposer();
  if (!document.querySelector("#outreach-modal").hidden) closeOutreach();
  if (!document.querySelector("#insights-modal").hidden) closeCompanyInsights();
  if (!document.querySelector("#commercial-intelligence-modal").hidden) closeCommercialIntelligence();
  if (!document.querySelector("#proposal-modal").hidden) closeProposal();
});

const shouldRestoreOpportunities = normalizeLegacyOpportunityHash();
window.addEventListener("hashchange", () => {
  if (!normalizeLegacyOpportunityHash()) return;
  requestAnimationFrame(() => scrollToOpportunities("auto"));
});

startClock();
Promise.all([
  loadPortalSession(),
  loadFeed(),
  loadOperations(),
  loadCommercialIntelligence().catch(error => {
    console.warn("Inteligência comercial temporariamente indisponível.", error);
    return {};
  })
])
  .then(([portalUser, feed, operations, intelligenceCases]) => {
    authenticatedPortalUser = portalUser;
    feedData = feed;
    operationsState = operations;
    lastOperationsSignature = operationsSignature(operations);
    commercialCases = intelligenceCases;
    previousDocumentJobs = Object.fromEntries(
      Object.entries(operations.document_jobs || {})
        .map(([processId, job]) => [processId, job.status])
    );
    renderBrand(feed, authenticatedPortalUser);
    renderKpis(feed);
    renderQueues(feed);
    renderEvents(feed);
    renderOpportunities(feed);
    renderInsights(feed);
    renderSummary(feed);
    renderRouteNavigation(feed);
    renderOperationalPulse();
    if (shouldRestoreOpportunities) {
      requestAnimationFrame(() => scrollToOpportunities("auto"));
    } else {
      window.scrollTo({ top: window.scrollY, left: 0, behavior: "auto" });
    }
    scheduleOperationalRefresh(
      operations.storage === "LOCAL_FALLBACK" ? 30000 : 5000
    );
  })
  .catch(error => {
    console.error(error);
    if (error.message === "Sessão encerrada.") return;
    alert(`Não foi possível iniciar o portal: ${error.message}`);
  });

window.addEventListener("pageshow", event => {
  if (!event.persisted) return;
  loadPortalSession().catch(() => window.location.replace("/login"));
});

let opportunityResizeFrame = 0;
window.addEventListener("resize", () => {
  if (!feedData) return;
  cancelAnimationFrame(opportunityResizeFrame);
  opportunityResizeFrame = requestAnimationFrame(() => {
    const nextPageSize = opportunityPageSize();
    if (nextPageSize === lastOpportunityPageSize) return;
    currentOpportunityPage = 1;
    renderOpportunities(feedData, lastOpportunityQuery);
  });
});
