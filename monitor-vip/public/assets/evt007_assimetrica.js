const state = { feed: null, opportunities: [], selected: null };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBrl(value, compact = false) {
  const n = Number(value) || 0;
  if (compact && Math.abs(n) >= 1_000_000) return `R$ ${(n / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MM`;
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(n);
}

function parsePercent(value, fallback = 5) {
  const n = Number(String(value ?? "").replace("%", "").replace(",", "."));
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function stableNumber(seed, min, max) {
  let h = 2166136261;
  for (const ch of String(seed)) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 16777619);
  }
  const normalized = (h >>> 0) / 4294967295;
  return Math.round(min + normalized * (max - min));
}

function severity(score) {
  if (score >= 80) return ["Crítica", "critica"];
  if (score >= 65) return ["Alta", "alta"];
  if (score >= 45) return ["Moderada", "moderada"];
  return ["Baixa", "baixa"];
}

function normalizeOpportunity(item, index) {
  const seed = `${item.fornecedor_cnpj || item.fornecedor || index}|${item.processo || ""}`;
  const value = Number(item.valor_numero) || 0;
  const guaranteePct = parsePercent(item.percentual_garantia_execucao, item.garantia_execucao === "SIM" ? 5 : 5);
  const guarantee = value * (guaranteePct / 100);
  const scores = {
    RNA: stableNumber(`${seed}:rna`, 38, 88),
    IAC: stableNumber(`${seed}:iac`, 35, 92),
    IAP: stableNumber(`${seed}:iap`, 32, 94),
    IAH: stableNumber(`${seed}:iah`, 30, 86),
    IAG: stableNumber(`${seed}:iag`, 36, 90),
    IU: stableNumber(`${seed}:iu`, 38, 89),
    IPC: stableNumber(`${seed}:ipc`, 28, 82),
    CONF: stableNumber(`${seed}:conf`, 72, 95)
  };
  const avg = Math.round((scores.IAC + scores.IAP + scores.IAH + scores.IAG + scores.IU) / 5);
  const ipm = Math.round((avg * .55) + (scores.RNA * .30) + (scores.CONF * .15));
  const mission = ipm >= 76 ? "Missão recomendada" : ipm >= 51 ? "Missão potencial" : ipm >= 26 ? "Corretagem premium" : "Corretagem simples";
  const asym = [
    ["Capacidade", scores.IAC], ["Precificação", scores.IAP], ["Histórico", scores.IAH],
    ["Crescimento", scores.IAG], ["Pressão contratual", scores.IPC]
  ].sort((a,b) => b[1] - a[1]);
  const dominant = asym[0][0];
  const potentialConsulting = mission.includes("Missão") ? Math.max(18000, guarantee * .004) : mission.includes("premium") ? Math.max(12000, guarantee * .002) : 0;
  const potentialBrokerage = guarantee * .012;
  return {
    ...item,
    _index: index,
    _value: value,
    _guaranteePct: guaranteePct,
    _guarantee: guarantee,
    _scores: scores,
    _asymmetry: avg,
    _ipm: ipm,
    _mission: mission,
    _dominant: dominant,
    _potentialConsulting: potentialConsulting,
    _potentialBrokerage: potentialBrokerage,
    _potentialTotal: potentialConsulting + potentialBrokerage
  };
}

async function loadFeed() {
  try {
    const cloud = await fetch("./api/feed", { cache: "no-store", credentials: "same-origin" });
    if (cloud.ok) return cloud.json();
  } catch (_) {}
  const fallback = await fetch("./data/monitor_feed_real.json", { cache: "no-store" });
  if (!fallback.ok) throw new Error("Feed indisponível.");
  return fallback.json();
}

function renderSummary(items) {
  const highAsym = items.filter(x => x._asymmetry >= 65).length;
  const highRna = items.filter(x => x._scores.RNA >= 60).length;
  const mission = items.filter(x => x._ipm >= 51).length;
  const guarantee = items.reduce((sum, x) => sum + x._guarantee, 0);
  const revenue = items.reduce((sum, x) => sum + x._potentialTotal, 0);
  $("#kpi-open").textContent = items.length;
  $("#kpi-asym").textContent = highAsym;
  $("#kpi-rna").textContent = highRna;
  $("#kpi-mission").textContent = mission;
  $("#kpi-guarantee").textContent = formatBrl(guarantee, true);
  $("#kpi-revenue").textContent = formatBrl(revenue, true);
}

function renderScores(item) {
  const labels = {
    RNA: ["RNA", "Risco de não assinatura"],
    IAC: ["IAC", "Assimetria de capacidade"],
    IAP: ["IAP", "Assimetria de precificação"],
    IAH: ["IAH", "Assimetria de histórico"],
    IAG: ["IAG", "Assimetria de crescimento"],
    IU: ["IU", "Urgência"],
    IPC: ["IPC", "Pressão contratual"],
    CONF: ["SINAL", "Confiança do sinal"]
  };
  $("#score-grid").innerHTML = Object.entries(item._scores).map(([key, value]) => `
    <div class="score">
      <div class="score-top"><span>${labels[key][0]}</span><strong>${value}</strong></div>
      <div class="bar"><i style="width:${value}%"></i></div>
      <small>${labels[key][1]}</small>
    </div>
  `).join("");
}

function renderAsymmetries(item) {
  const rows = [
    ["Assimetria de Capacidade", item._scores.IAC],
    ["Assimetria Patrimonial", Math.round((item._scores.IAC + item._scores.IAG) / 2)],
    ["Assimetria de Crescimento", item._scores.IAG],
    ["Assimetria de Histórico", item._scores.IAH],
    ["Assimetria de Precificação", item._scores.IAP],
    ["Assimetria de Garantia", Math.round((item._scores.RNA + item._scores.IAC) / 2)],
    ["Assimetria Jurídica", stableNumber(`${item.processo}:legal`, 20, 70)],
    ["Assimetria Operacional", Math.round((item._scores.IAC + item._scores.IAH) / 2)]
  ].sort((a,b) => b[1] - a[1]);
  $("#asymmetry-list").innerHTML = rows.slice(0, 6).map(([name, score]) => {
    const [label, cls] = severity(score);
    return `<div class="asymmetry-row"><span>${escapeHtml(name)}</span><span class="severity ${cls}">${label}</span></div>`;
  }).join("");
  $("#dominant-asym").textContent = item._dominant;
}

function renderPerspectives(item) {
  const market = [];
  if (item._scores.IAC >= 60) market.push("Necessidade de limite relevante frente ao porte da obrigação.");
  if (item._scores.IAG >= 60) market.push("Crescimento contratual potencialmente superior à escala histórica.");
  if (item._scores.IAP >= 60) market.push("Precificação vencedora exige leitura de margem e capacidade de execução.");
  if (item._scores.IAH >= 60) market.push("Experiência equivalente precisa ser comprovada com mais profundidade.");
  if (!market.length) market.push("Sem desencaixe crítico evidente nos sinais disponíveis nesta etapa.");

  const system = [
    item.garantia_execucao === "SIM" ? "Necessidade de garantia já sinalizada na base documental." : "Necessidade de garantia ainda requer confirmação documental.",
    item.insights_empresa?.oportunidades_na_base > 1 ? `Empresa já observada em ${item.insights_empresa.oportunidades_na_base} oportunidades da base.` : "Empresa ainda com baixa recorrência observada na base.",
    `Confiança demonstrativa do sinal: ${item._scores.CONF}%.`,
    `Rota atual da oportunidade: ${item.rota || "a confirmar"}.`
  ];
  $("#market-view").innerHTML = market.map(x => `<li>${escapeHtml(x)}</li>`).join("");
  $("#system-view").innerHTML = system.map(x => `<li>${escapeHtml(x)}</li>`).join("");
}

function renderMission(item) {
  $("#ipm-score").textContent = item._ipm;
  $("#ipm-label").textContent = item._mission;
  $("#ipm-explanation").textContent = item._ipm >= 76
    ? "Há combinação de assimetria, risco de fricção e confiança suficiente para recomendar leitura consultiva prioritária."
    : item._ipm >= 51
      ? "Os sinais justificam aprofundamento antes da abordagem comercial."
      : "A oportunidade tende a exigir menos reconstrução e maior foco na colocação/corretagem.";
}

function renderNeck(item) {
  const bullets = [];
  if (item._guarantee > 0) bullets.push(`Garantia estimada de ${formatBrl(item._guarantee, true)}.`);
  if (item._scores.IU >= 60) bullets.push("Janela de intervenção potencialmente curta até convocação/assinatura.");
  if (item._scores.IAG >= 60) bullets.push("Crescimento acima da escala histórica inferida para o caso.");
  if (item._scores.IAH >= 60) bullets.push("Histórico equivalente requer confirmação antes da apresentação ao mercado.");
  if (item._scores.IAP >= 70) bullets.push("Precificação pode pressionar a leitura de capacidade de execução.");
  if (!bullets.length) bullets.push("Nenhuma pressão crítica foi inferida na demonstração atual.");
  $("#neck-list").innerHTML = bullets.slice(0, 4).map(x => `<li>${escapeHtml(x)}</li>`).join("");
  const pressureScore = Math.round((item._scores.RNA + item._scores.IU + item._scores.IPC) / 3);
  $("#pressure-level").textContent = `${severity(pressureScore)[0]} pressão`;
}

function renderRoute(item) {
  let model = "MODELO 3 — Somente Corretagem";
  let reason = "Assimetria limitada; foco provável na colocação.";
  if (item._ipm >= 51) {
    model = "MODELO 1 — Consultoria + Corretagem";
    reason = "Assimetria relevante + necessidade provável de estruturação e colocação.";
  } else if (item._asymmetry >= 65 && !String(item.rota || "").toLowerCase().includes("vazquez")) {
    model = "MODELO 2 — Somente Consultoria";
    reason = "Assimetria relevante; corretagem pode permanecer com terceiro.";
  }
  $("#route-model").textContent = model;
  $("#route-why").textContent = reason;
}

function renderSelected(item) {
  state.selected = item;
  $("#hero-company").textContent = item.fornecedor || "Empresa vencedora";
  $("#hero-org").textContent = item.orgao || "—";
  $("#hero-process").textContent = item.abordagem?.edital || item.processo || "—";
  $("#hero-object").textContent = item.objeto || "—";
  $("#hero-date").textContent = item.data_homologacao || "—";
  $("#hero-value").textContent = item.valor || formatBrl(item._value);
  $("#hero-term").textContent = item.prazo_contrato || "A confirmar no edital";
  $("#hero-place").textContent = [item.cidade, item.uf || item.estado].filter(Boolean).join(" / ") || "A confirmar";
  $("#econ-contract").textContent = formatBrl(item._value, true);
  $("#econ-guarantee").textContent = formatBrl(item._guarantee, true);
  $("#econ-percent").textContent = `${item._guaranteePct.toLocaleString("pt-BR")}%`;
  $("#econ-total").textContent = formatBrl(item._potentialTotal, true);
  $("#hero-status").textContent = `${item.evento || "EVT-007"} · Homologado`;
  renderRoute(item);
  renderAsymmetries(item);
  renderScores(item);
  renderPerspectives(item);
  renderMission(item);
  renderNeck(item);
  $("#next-action-title").textContent = item._ipm >= 76 ? "Aprofundar antes de abordar" : item.documentos?.length ? "Ler a evidência documental" : "Confirmar edital e garantia";
  $("#next-action-copy").textContent = item._ipm >= 51
    ? "Entender a fragilidade sem antecipar a solução; validar edital, capacidade e timing antes de posicionar a missão."
    : "Confirmar obrigação de garantia e abrir relacionamento com abordagem objetiva.";
  $$(".opp-row").forEach(row => row.classList.toggle("active", Number(row.dataset.index) === item._index));
}

function renderList(items) {
  $("#opportunity-count").textContent = `${items.length} oportunidades`;
  $("#opportunity-list").innerHTML = items.slice(0, 20).map(item => `
    <div class="opp-row" data-index="${item._index}">
      <div class="opp-name"><strong>${escapeHtml(item.fornecedor || "Empresa vencedora")}</strong><small>${escapeHtml(item.orgao || "—")} · ${escapeHtml(item.objeto || "—")}</small></div>
      <div class="opp-metric"><span>Assimetria</span><strong>${item._asymmetry}</strong></div>
      <div class="opp-metric"><span>RNA</span><strong>${item._scores.RNA}</strong></div>
      <div class="opp-metric"><span>IPM</span><strong>${item._ipm}</strong></div>
      <div class="opp-metric"><span>Valor</span><strong>${formatBrl(item._value, true)}</strong></div>
      <button class="opp-open" type="button" data-open="${item._index}">Abrir</button>
    </div>
  `).join("");
  $$('[data-open]').forEach(button => button.addEventListener("click", () => {
    const item = state.opportunities.find(x => x._index === Number(button.dataset.open));
    if (item) { renderSelected(item); $("#hero-card").scrollIntoView({ behavior: "smooth", block: "start" }); }
  }));
}

function filterList(query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return renderList(state.opportunities);
  renderList(state.opportunities.filter(item => [item.fornecedor,item.orgao,item.objeto,item.processo,item.fornecedor_cnpj].some(v => String(v || "").toLowerCase().includes(q))));
}

function bindActions() {
  $("#search").addEventListener("input", e => filterList(e.target.value));
  $("#refresh").addEventListener("click", () => window.location.reload());
  $$('[data-action]').forEach(button => button.addEventListener("click", () => {
    const labels = {
      document: "Motor documental: localizar, preservar, indexar e ler a regra de garantia.",
      "decision-maker": "OSINT/relacionamento: identificar decisor e contexto sem bloquear o fluxo factual.",
      email: "Próxima integração: gerar abordagem contextualizada e submetê-la à revisão humana.",
      proposal: "Próxima integração: proposta conforme rota Modelo 1, 2 ou 3.",
      "follow-up": "Próxima integração: registrar contato, próximo passo e memória de relacionamento."
    };
    alert(labels[button.dataset.action] || "Ação em construção.");
  }));
}

async function boot() {
  try {
    const feed = await loadFeed();
    state.feed = feed;
    state.opportunities = (feed.opportunities || []).map(normalizeOpportunity)
      .filter(item => item.evento === "EVT-007" || !item.evento)
      .sort((a,b) => b._ipm - a._ipm || b._value - a._value);
    renderSummary(state.opportunities);
    renderList(state.opportunities);
    if (state.opportunities[0]) renderSelected(state.opportunities[0]);
    $("#data-status").textContent = `Protótipo visual · fonte ${feed.cloud?.storage || "feed preservado"} · índices demonstrativos até ligação do motor OSINT`;
  } catch (error) {
    $("#data-status").textContent = `Falha ao carregar: ${error.message}`;
  }
}

bindActions();
boot();
