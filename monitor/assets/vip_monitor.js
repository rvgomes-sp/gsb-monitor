let feedData = null;
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
let currentProposalText = "";

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

async function loadFeed() {
  const response = await fetch("./data/monitor_feed_real.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Feed de oportunidades indisponível.");
  return response.json();
}

async function loadOperations() {
  // /api/operations e opcional (CRM). Se nao existir backend, segue com estado vazio.
  try {
    const response = await fetch("./api/operations", { cache: "no-store" });
    if (!response.ok) throw new Error("sem backend");
    return await response.json();
  } catch (e) {
    return { outreach: {}, proposals: [], counters: {}, document_jobs: {} };
  }
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

function renderBrand(feed) {
  document.querySelector("#brand-title").textContent = feed.brand.title;
  document.querySelector("#brand-subtitle").textContent = feed.brand.subtitle;
  document.querySelector("#signature-name").textContent = feed.brand.signature;
  document.querySelector("#signature-message").textContent = `"${feed.brand.message}"`;
  document.querySelector("#operator-name").textContent = feed.operator?.name || "Ana Fonseca";
  document.querySelector("#operator-role").textContent = feed.operator?.role || "Diretora Institucional";
  document.querySelector("#operator-initials").textContent = feed.operator?.initials || "AF";
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

function renderQueues(feed) {
  document.querySelector("#queues").innerHTML = feed.queues.map(queue => `
    <section class="card queue ${queue.priority === "high" ? "high" : ""}">
      <small>${escapeHtml(queue.subtitle)}</small>
      <h3>${escapeHtml(queue.event_id)}<br>${escapeHtml(queue.label)}</h3>
      <p>${escapeHtml(queue.count)} registros</p>
      <a href="#opportunities-section" class="btn">${escapeHtml(queue.button)}<span>→</span></a>
    </section>
  `).join("");
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

function renderOpportunities(feed, query = "") {
  const normalized = query.trim().toLocaleLowerCase("pt-BR");
  const opportunities = normalized
    ? feed.opportunities.filter(item => [
        item.orgao,
        item.processo,
        item.fornecedor,
        item.fornecedor_cnpj,
        item.objeto,
        item.modalidade
      ].join(" ").toLocaleLowerCase("pt-BR").includes(normalized))
    : feed.opportunities;

  document.querySelector("#opportunities").innerHTML = opportunities.map(item => {
    const guarantee = item.percentual_garantia_execucao
      ? `${item.status} · ${item.percentual_garantia_execucao}`
      : item.status;
    return `
      <tr>
        <td>${escapeHtml(item.orgao)}</td>
        <td>${escapeHtml(item.processo)}</td>
        <td><strong>${escapeHtml(item.fornecedor || "Não informado")}</strong><br><small>${escapeHtml(item.porte || "")}</small></td>
        <td>${escapeHtml(item.fornecedor_cnpj || "")}</td>
        <td>${escapeHtml(item.objeto)}</td>
        <td>${escapeHtml(item.modalidade || "")}</td>
        <td>${escapeHtml(item.data_homologacao || "")}</td>
        <td>${escapeHtml(item.evento)}</td>
        <td><span class="status ${statusClass(item.status)}">${escapeHtml(guarantee)}</span></td>
        <td class="documents-cell">${documentCell(item)}</td>
        <td class="operations-cell">${operationCell(item)}</td>
        <td>${escapeHtml(item.valor)}</td>
        <td>${escapeHtml(item.rota)}</td>
        <td>${escapeHtml(item.atualizado)}</td>
      </tr>
    `;
  }).join("");

  bindOpportunityActions(feed);
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
    const previous = previousDocumentJobs;
    operationsState = operations;
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
    data: { ...data, operator: "Ana Fonseca" }
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
      notes: document.querySelector("#proposal-notes").value
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
  if (feedData) renderOpportunities(feedData, event.target.value);
});
document.querySelectorAll("[data-close-email-modal]").forEach(button => button.addEventListener("click", closeEmailComposer));
document.querySelectorAll("[data-close-outreach]").forEach(button => button.addEventListener("click", closeOutreach));
document.querySelectorAll("[data-close-insights]").forEach(button => button.addEventListener("click", closeCompanyInsights));
document.querySelectorAll("[data-close-proposal]").forEach(button => button.addEventListener("click", closeProposal));
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
  if (!document.querySelector("#proposal-modal").hidden) closeProposal();
});

startClock();
Promise.all([loadFeed(), loadOperations().catch(() => ({ outreach: {}, proposals: [], counters: {}, document_jobs: {} }))])
  .then(([feed, operations]) => {
    feedData = feed;
    operationsState = operations || { outreach: {}, proposals: [], counters: {}, document_jobs: {} };
    previousDocumentJobs = Object.fromEntries(
      Object.entries(operations.document_jobs || {})
        .map(([processId, job]) => [processId, job.status])
    );
    renderBrand(feed);
    renderKpis(feed);
    renderQueues(feed);
    renderEvents(feed);
    renderOpportunities(feed);
    renderInsights(feed);
    renderSummary(feed);
    renderOperationalPulse();
    setInterval(refreshOperationalState, 5000);
  })
  .catch(error => {
    console.error(error);
    alert(`Não foi possível iniciar o portal: ${error.message}`);
  });
