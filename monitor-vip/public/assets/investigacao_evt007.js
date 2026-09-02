const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const state = { feed: null, cases: {}, operations: null, user: null, selected: null, dossier: null };

function esc(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");}
function brl(v){return new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:0}).format(Number(v)||0);}
function compact(v){const n=Number(v)||0;return Math.abs(n)>=1e6?`R$ ${(n/1e6).toLocaleString("pt-BR",{maximumFractionDigits:1})} MM`:brl(n);}
function normalizeCnpj(v){return String(v||"").replace(/\D/g,"");}
function param(name){return new URLSearchParams(location.search).get(name);}

async function getJson(url){const r=await fetch(url,{cache:"no-store",credentials:"same-origin"});if(!r.ok)throw new Error(`${url}: ${r.status}`);return r.json();}
async function load(){
  const [feed,cases,ops,user] = await Promise.all([
    getJson("./api/feed").catch(()=>getJson("./data/monitor_feed_real.json")),
    getJson("./data/commercial_intelligence_cases.json").catch(()=>({cases:{}})),
    getJson("./api/operations").catch(()=>({outreach:{},proposals:[],document_jobs:{}})),
    getJson("./api/auth/session").catch(()=>({user:{name:"Usuário",role:"",initials:"US"}}))
  ]);
  state.feed=feed;state.cases=cases.cases||{};state.operations=ops;state.user=user.user||user;
}

function confidenceLabel(dossier){
  const c=dossier?.documentaryReading?.confidence;
  if(c==="ALTA") return "ALTA";
  if(c==="MEDIA") return "MODERADA";
  if(c==="BAIXA") return "BAIXA";
  return "EM ABERTURA";
}

function evidence(kind,title,detail){return {kind,title,detail};}
function buildEvidence(item,dossier){
  const out=[];
  if(item?.data_homologacao) out.push(evidence("confirmed","Homologação confirmada",`${item.evento||"EVT-007"} · ${item.data_homologacao}`));
  if(item?.valor_numero) out.push(evidence("confirmed","Valor homologado",item.valor||brl(item.valor_numero)));
  if(item?.garantia_execucao==="SIM" || dossier?.guarantee?.executionPercent) out.push(evidence("confirmed","Garantia identificada", dossier?.guarantee?.executionPercent ? `${dossier.guarantee.executionPercent}% do contrato` : item.percentual_garantia_execucao||"Exigência localizada"));
  if(dossier?.documentaryReading?.clauses?.length) out.push(evidence("confirmed","Leitura documental disponível",`${dossier.documentaryReading.clauses.length} achados registrados`));
  if(dossier?.portfolio?.contracts?.length) out.push(evidence("indicative","Carteira pública observada",`${dossier.portfolio.contracts.length} contratos encontrados na fonte consultada`));
  if(dossier?.limitStatus==="NAO_VERIFICADO") out.push(evidence("unknown","Limite segurador","Não verificado no caso atual"));
  if(!dossier) out.push(evidence("unknown","Dossiê investigativo","Ainda não estruturado para este processo"));
  return out;
}

function buildPains(item,dossier){
  const rows=[];
  if(dossier?.guarantee){
    const g=dossier.guarantee;
    const extra = g.laborCoveragePercent?.max || 0;
    rows.push(["Garantia / estruturação", extra>0?"Forte indício":"Em investigação", extra>0?"strong":"open"]);
  } else if(item?.garantia_execucao==="SIM") rows.push(["Garantia / estruturação","Em investigação","open"]);
  else rows.push(["Garantia / estruturação","Não confirmada","unknown"]);
  if(dossier?.positioning?.capacityReadiness?.level==="EXIGE_VALIDACAO_IMEDIATA") rows.push(["Capacidade / limite","Forte indício","strong"]);
  else rows.push(["Capacidade / limite","Não conhecida","unknown"]);
  if(dossier?.flags?.includes("LOGISTICA_DESAFIADORA")) rows.push(["Mobilização / operação","Forte indício","strong"]);
  else rows.push(["Mobilização / operação","Em investigação","open"]);
  rows.push(["Fiscal / CND","Sem evidência atual","clear"]);
  if(dossier?.documentaryReading?.clauses?.some(c=>c.classification==="DIVERGENCIA_DOCUMENTAL")) rows.push(["Contratual / cláusulas","Forte indício","strong"]);
  else rows.push(["Contratual / cláusulas","Em investigação","open"]);
  rows.push(["Seguradora / consumo de limite","Não conhecido","unknown"]);
  return rows;
}

function openQuestions(dossier){
  const q=[];
  if(dossier?.portfolio?.questions?.length) q.push(...dossier.portfolio.questions);
  q.push("Qual o limite disponível e o consumo atual junto ao mercado segurador?");
  q.push("Qual a data efetiva de convocação e o prazo para apresentação da garantia?");
  q.push("Quem conduz internamente a garantia e a formalização do contrato?");
  return [...new Set(q)].slice(0,6);
}

function renderEvidenceRows(items){return items.map(x=>`<div class="evidence-item"><span class="evidence-marker ${x.kind}">${x.kind==="confirmed"?"✓":x.kind==="indicative"?"◐":x.kind==="estimated"?"≈":"?"}</span><div><strong>${esc(x.title)}</strong><small>${esc(x.detail)}</small></div></div>`).join("");}

function renderSelected(item){
  const dossier=state.cases[item.processo]||null;state.selected=item;state.dossier=dossier;
  const g=dossier?.guarantee;
  const percent=g?.executionPercent || Number(String(item.percentual_garantia_execucao||"").replace("%","")) || null;
  const guaranteeValue=percent?Number(item.valor_numero||g?.contractValue||0)*(percent/100):null;
  $("#case-title").textContent=dossier?.caseName||item.fornecedor||"Caso em investigação";
  $("#event-company").textContent=item.fornecedor||dossier?.supplier||"—";
  $("#event-agency").textContent=item.orgao||dossier?.agency||"—";
  $("#event-process").textContent=item.abordagem?.edital||dossier?.tender||item.processo||"—";
  $("#event-object").textContent=item.objeto||dossier?.item||"—";
  $("#event-date").textContent=item.data_homologacao||dossier?.homologationAt||"—";
  $("#event-value").textContent=item.valor||compact(item.valor_numero||g?.contractValue);
  $("#event-guarantee").textContent=percent?`${percent}% · ${compact(guaranteeValue)}`:"A confirmar";
  $("#event-term").textContent=g?.executionTermMonths?`${g.executionTermMonths} meses`:"A confirmar";
  $("#thesis-confidence").textContent=confidenceLabel(dossier);
  $("#thesis-status").textContent=dossier?"EM INVESTIGAÇÃO":"ABERTURA";
  $("#thesis-copy").textContent=dossier?.positioning?.capacityReadiness?.explanation || "O caso foi aberto pela homologação. A hipótese comercial só será confirmada após leitura documental, capacidade, timing e sinais do tomador.";
  const pains=buildPains(item,dossier);
  $("#pain-list").innerHTML=pains.map(([name,label,cls])=>`<div class="pain-row"><span>${esc(name)}</span><span class="pain-badge ${cls}">${esc(label)}</span></div>`).join("");
  const ev=buildEvidence(item,dossier);$("#known-facts").innerHTML=renderEvidenceRows(ev);
  $("#open-questions").innerHTML=openQuestions(dossier).map(q=>`<li>${esc(q)}</li>`).join("");
  const hasStrong=pains.some(x=>x[2]==="strong");
  $("#conclusion-title").textContent=hasStrong?"Há indícios suficientes para aprofundar":"Caso ainda em investigação";
  $("#conclusion-copy").textContent=hasStrong?"A homologação já revelou pressões que justificam investigação dirigida. O sistema ainda distingue indício de dor confirmada antes de entregar a oportunidade como tese fechada.":"Ainda não há evidência suficiente para declarar dor comercial confirmada.";
  $("#ana-preview").href=`./carteira_ana.html?process=${encodeURIComponent(item.processo)}`;
  renderEvidenceTab(ev,dossier);
  renderCompany(item,dossier);
  renderPortfolio(dossier);
  renderGuarantee(item,dossier,guaranteeValue,percent);
  renderDecisionMakers(dossier);
  history.replaceState(null,"",`${location.pathname}?process=${encodeURIComponent(item.processo)}`);
}

function renderEvidenceTab(ev,dossier){
  const rows=[...ev];
  for(const c of dossier?.documentaryReading?.clauses||[]) rows.push(evidence(c.classification==="FATO_DOCUMENTAL"?"confirmed":"indicative",c.reference,c.finding));
  $("#evidence-table").innerHTML=`<div class="row head"><span>Natureza</span><span>Evidência</span><span>Status</span><span>Fonte</span></div>`+rows.map(r=>`<div class="row"><span>${r.kind==="confirmed"?"Confirmado":r.kind==="indicative"?"Indício":r.kind==="estimated"?"Estimado":"Não conhecido"}</span><span>${esc(r.title)} — ${esc(r.detail)}</span><span>${r.kind==="confirmed"?"✓":"◐"}</span><span>${r.title.includes("TR ")?"Documento":"Base atual"}</span></div>`).join("");
}
function renderCompany(item,dossier){
  $("#company-name").textContent=item.fornecedor||dossier?.supplier||"—";
  const data=[
    ["CNPJ",item.fornecedor_cnpj||dossier?.supplierCnpj||"—"],
    ["Porte",item.porte||"Não informado"],
    ["Natureza jurídica",item.natureza_juridica||"Não informada"],
    ["Histórico observado",dossier?.positioning?.marketHistory||"Ainda não consolidado"],
    ["Governança",dossier?.positioning?.governanceEvidence||"Ainda não consolidada"],
    ["Grupo econômico","Não estruturado neste dossiê"]
  ];
  $("#company-profile").innerHTML=data.map(([a,b])=>`<div><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join("");
}
function renderPortfolio(dossier){
  const contracts=dossier?.portfolio?.contracts||[];const total=contracts.reduce((s,c)=>s+(Number(c.value)||0),0);const vigente=contracts.filter(c=>c.status==="VIGENTE").length;
  $("#portfolio-summary").innerHTML=[['Contratos observados',contracts.length],['Vigentes',vigente],['Valor observado',compact(total)],['Saldo executável','Conectar motor pronto']].map(([a,b])=>`<div><span>${a}</span><strong>${b}</strong></div>`).join("");
  $("#portfolio-contracts").innerHTML=contracts.length?contracts.map(c=>`<div class="contract-row"><span>${esc(c.number)}</span><span>${esc(c.signedAt)}</span><span>${compact(c.value)}</span><span>${esc(c.status)}</span></div>`).join(""):`<div class="evidence-item"><span class="evidence-marker unknown">?</span><div><strong>Carteira contratual ainda não estruturada</strong><small>O motor de fluxo poderá abastecer esta área sem duplicar a fonte.</small></div></div>`;
}
function renderGuarantee(item,dossier,value,percent){
  const g=dossier?.guarantee||{};const details=[['Percentual principal',percent?`${percent}%`:'A confirmar'],['Valor estimado',value?compact(value):'A confirmar'],['Prazo',g.executionTermMonths?`${g.executionTermMonths} meses`:'A confirmar'],['Validade adicional',g.additionalValidityDays?`${g.additionalValidityDays} dias`:'A confirmar'],['Seguro garantia',g.insuranceAccepted===true?'Admitido':'A confirmar'],['Revisão humana',dossier?.documentaryReading?.humanReview||'Pendente']];
  $("#guarantee-details").innerHTML=details.map(([a,b])=>`<div><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join("");
  const insurer=[evidence("unknown","Limite disponível","Não público / não verificado"),evidence("unknown","Consumo atual de limite","Não conhecido"),evidence("unknown","Recusas internas","Não conhecidas"),evidence("indicative","Pressão de taxa",dossier?.positioning?.ratePressure?.label||"Ainda não investigada")];
  $("#insurer-view").innerHTML=renderEvidenceRows(insurer);
}
function renderDecisionMakers(dossier){
  const rows=dossier?.approachMap||[];$("#decision-makers").innerHTML=rows.length?rows.map(r=>`<div class="decision-row"><span class="decision-rank">${r.priority}</span><div><strong>${esc(r.decisionMaker)}</strong><small>${esc(r.area)}</small></div><div><strong>${esc(r.primaryChannel)}</strong><small>Canal</small></div><div><strong>${esc(r.confidence)}</strong><small>Confiança</small></div><div><strong>${esc(r.objective)}</strong><small>Objetivo</small></div></div>`).join(""):`<div class="evidence-item"><span class="evidence-marker unknown">?</span><div><strong>Decisores ainda não estruturados</strong><small>Buscar financeiro, licitações, jurídico/contratos e operação conforme a dor.</small></div></div>`;
}

function filtered(query){const q=query.trim().toLowerCase();return !q?state.feed.opportunities:state.feed.opportunities.filter(x=>[x.fornecedor,x.orgao,x.processo,x.objeto].join(' ').toLowerCase().includes(q));}
function bind(){
  $$("[data-tab]").forEach(b=>b.addEventListener("click",()=>{$$("[data-tab]").forEach(x=>x.classList.toggle("active",x===b));$$("[data-panel]").forEach(p=>p.classList.toggle("active",p.dataset.panel===b.dataset.tab));}));
  $("#show-evidence").addEventListener("click",()=>document.querySelector('[data-tab="evidence"]').click());
  $("#case-search").addEventListener("change",e=>{const list=filtered(e.target.value);if(list[0])renderSelected(list[0]);});
}

async function main(){
  try{await load();const u=state.user||{};$("#operator-name").textContent=u.name||"Usuário";$("#operator-role").textContent=u.role||u.email||"";$("#operator-initials").textContent=u.initials||"US";bind();const wanted=param("process");const item=state.feed.opportunities.find(x=>x.processo===wanted)||state.feed.opportunities.find(x=>state.cases[x.processo])||state.feed.opportunities[0];if(item)renderSelected(item);$("#data-status").textContent=`Fonte: ${state.feed.cloud?.storage||"feed"} · ${state.feed.cloud?.updated_at||state.feed.generated_at||"atual"}`;}catch(e){$("#data-status").textContent=`Falha ao carregar: ${e.message}`;console.error(e);}}
main();
