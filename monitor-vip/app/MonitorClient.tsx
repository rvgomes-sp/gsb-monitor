"use client";

import { useEffect, useMemo, useState } from "react";

type DocumentLink = { label: string; url: string };
type Opportunity = {
  orgao: string;
  processo: string;
  fornecedor: string;
  fornecedor_cnpj: string;
  porte: string;
  natureza_juridica: string;
  objeto: string;
  modalidade: string;
  data_homologacao: string;
  evento: string;
  status: string;
  garantia_execucao?: string;
  percentual_garantia_execucao?: string;
  seguro_garantia_execucao?: string;
  documentos?: DocumentLink[];
  valor_numero: number;
  valor: string;
  rota: string;
  atualizado: string;
};
type Feed = {
  meta: Record<string, unknown>;
  kpis: Array<{ label: string; value: string | number; detail?: string }>;
  opportunities: Opportunity[];
};
type Outreach = {
  status?: string;
  decisionMaker?: string;
  decision_maker?: string;
  email?: string;
  phone?: string;
  lastContactAt?: string;
  last_contact_at?: string;
  sentAt?: string;
  sent_at?: string;
  nextFollowUpAt?: string;
  next_follow_up_at?: string;
  subject?: string;
  body?: string;
  notes?: string;
};
type Operations = {
  storage?: string;
  outreach: Record<string, Outreach>;
  proposals: Array<Record<string, unknown>>;
};

const statuses = [
  ["NAO_INICIADO", "Não iniciado"],
  ["EM_PREPARACAO", "Em preparação"],
  ["PRONTO_PARA_ENVIO", "Pronto para envio"],
  ["ENVIADO", "Enviado"],
  ["AGUARDANDO_RETORNO", "Aguardando retorno"],
  ["RESPONDEU", "Respondeu"],
  ["PROPOSTA_EM_PREPARACAO", "Proposta em preparação"],
  ["PROPOSTA_ENVIADA", "Proposta enviada"],
  ["NEGOCIACAO", "Negociação"],
  ["FECHADO", "Fechado"],
  ["SEM_INTERESSE", "Sem interesse"],
] as const;

const blankOperations: Operations = { outreach: {}, proposals: [] };

function text(value: unknown) {
  const raw = String(value ?? "");
  if (!/[ÃÂ]/.test(raw)) return raw;
  try {
    const bytes = Uint8Array.from(raw, (char) => char.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
  } catch {
    return raw;
  }
}

function brl(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

function normalize(record?: Outreach): Outreach {
  if (!record) return {};
  return {
    ...record,
    decision_maker: record.decision_maker ?? record.decisionMaker ?? "",
    last_contact_at: record.last_contact_at ?? record.lastContactAt ?? "",
    sent_at: record.sent_at ?? record.sentAt ?? "",
    next_follow_up_at: record.next_follow_up_at ?? record.nextFollowUpAt ?? "",
  };
}

function guaranteeLabel(opportunity: Opportunity) {
  if (opportunity.garantia_execucao === "SIM") {
    return opportunity.percentual_garantia_execucao
      ? `${opportunity.percentual_garantia_execucao} de garantia`
      : "Garantia identificada";
  }
  return "Leitura pendente";
}

function buildEmail(opportunity: Opportunity, decisionMaker: string) {
  const addressee = decisionMaker || "[NOME DO DECISOR]";
  const guarantee =
    opportunity.garantia_execucao === "SIM"
      ? `A leitura documental identificou garantia de execução de ${opportunity.percentual_garantia_execucao || "percentual previsto no instrumento"}, com valor segurado estimado conforme a contratação.`
      : "Nossa equipe está acompanhando a formalização contratual para validar a exigência e as condições da garantia de execução.";
  return {
    subject: `Homologação — ${text(opportunity.modalidade)} | ${text(opportunity.fornecedor)}`,
    body: `Prezado(a) ${addressee},

Meu nome é Ana Fonseca, Diretora Institucional da Vazquez & Fonseca.

Por meio do nosso modelo de acompanhamento contínuo das contratações públicas, identificamos a homologação da contratação ${opportunity.processo}, em favor da ${text(opportunity.fornecedor)}, no valor de ${brl(opportunity.valor_numero)}.

${guarantee}

A Vazquez & Fonseca atua na concessão e gestão de limite, apoio técnico à subscrição, estruturação e emissão da apólice, além do acompanhamento durante toda a vigência do contrato — especialmente em renovações, prorrogações e aditivos.

Gostaria de confirmar se este tema está sob sua responsabilidade ou com quem poderíamos tratar da estruturação e do acompanhamento da garantia.

Atenciosamente,

Ana Fonseca
Diretora Institucional
Vazquez & Fonseca`,
  };
}

export default function MonitorClient({ authenticatedUser }: { authenticatedUser: string }) {
  const [feed, setFeed] = useState<Feed | null>(null);
  const [operations, setOperations] = useState<Operations>(blankOperations);
  const [query, setQuery] = useState("");
  const [route, setRoute] = useState("TODAS");
  const [selected, setSelected] = useState<Opportunity | null>(null);
  const [modal, setModal] = useState<"contact" | "email" | "proposal" | "documents" | null>(null);
  const [form, setForm] = useState<Outreach>({});
  const [cloudDocuments, setCloudDocuments] = useState<DocumentLink[]>([]);
  const [message, setMessage] = useState("");
  const [clock, setClock] = useState(new Date());

  async function refreshOperations() {
    const response = await fetch("/api/operations", { cache: "no-store" });
    if (!response.ok) throw new Error("Não foi possível carregar o controle operacional.");
    setOperations(await response.json());
  }

  useEffect(() => {
    Promise.all([
      fetch("/api/feed", { cache: "no-store" }).then((response) =>
        response.ok
          ? response.json()
          : fetch("/data/monitor_feed_real.json").then((fallback) => fallback.json()),
      ),
      fetch("/api/operations", { cache: "no-store" }).then((response) => response.json()),
    ]).then(([feedData, operationData]) => {
      setFeed(feedData);
      if (!operationData.error) setOperations(operationData);
    }).catch(() => setMessage("Não foi possível carregar todos os dados."));
    const timer = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const opportunities = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("pt-BR");
    return (feed?.opportunities ?? []).filter((item) => {
      const routeMatch = route === "TODAS" || item.rota === route;
      const searchMatch = !needle || [
        item.orgao, item.processo, item.fornecedor, item.fornecedor_cnpj,
        item.objeto, item.modalidade,
      ].some((value) => text(value).toLocaleLowerCase("pt-BR").includes(needle));
      return routeMatch && searchMatch;
    });
  }, [feed, query, route]);

  const stats = useMemo(() => {
    const contacts = Object.values(operations.outreach).map(normalize);
    const today = new Date().toISOString().slice(0, 10);
    return {
      total: feed?.opportunities.length ?? 0,
      vf: feed?.opportunities.filter((item) => item.rota.includes("Vazquez")).length ?? 0,
      vm: feed?.opportunities.filter((item) => item.rota.includes("Vieira")).length ?? 0,
      pipeline: contacts.filter((item) => item.status && item.status !== "NAO_INICIADO").length,
      due: contacts.filter((item) => item.next_follow_up_at === today).length,
      overdue: contacts.filter((item) => item.next_follow_up_at && item.next_follow_up_at < today && !["FECHADO", "SEM_INTERESSE"].includes(item.status ?? "")).length,
    };
  }, [feed, operations]);

  async function open(opportunity: Opportunity, target: typeof modal) {
    const current = normalize(operations.outreach[opportunity.processo]);
    setSelected(opportunity);
    setForm(current);
    setModal(target);
    setMessage("");
    if (target === "documents") {
      setCloudDocuments([]);
      const response = await fetch(
        `/api/documents?process_id=${encodeURIComponent(opportunity.processo)}`,
        { cache: "no-store" },
      );
      if (response.ok) {
        const result = await response.json();
        setCloudDocuments(result.documents ?? []);
      }
    }
  }

  async function saveContact(overrides: Partial<Outreach> = {}) {
    if (!selected) return;
    const data = { ...form, ...overrides, operator: "Usuário autenticado" };
    const response = await fetch("/api/outreach", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ process_id: selected.processo, data }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error ?? "Falha ao salvar.");
    await refreshOperations();
    setMessage("Controle salvo no banco da nuvem.");
    return result;
  }

  async function registerSent(subject: string, body: string) {
    const followUp = new Date();
    followUp.setDate(followUp.getDate() + 3);
    await saveContact({
      status: "ENVIADO",
      subject,
      body,
      sent_at: new Date().toISOString(),
      next_follow_up_at: followUp.toISOString().slice(0, 10),
    });
  }

  if (!feed) {
    return <main className="loading"><div className="brand-mark">VF</div><p>Preparando o GSB Monitor…</p></main>;
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">VF</div><div><strong>GSB Monitor</strong><span>Intelligence Platform</span></div></div>
        <nav>
          <button className="active">Visão executiva</button>
          <button onClick={() => document.getElementById("oportunidades")?.scrollIntoView({ behavior: "smooth" })}>Oportunidades</button>
          <button>Monitoramento</button>
          <button>Documentos</button>
          <button>Relatórios</button>
        </nav>
        <div className="sidebar-note"><i></i> Ambiente protegido<br/><span>Base operacional em nuvem</span></div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div><p className="eyebrow">VF Intelligence Platform</p><h1>Oportunidades que pedem ação.</h1></div>
          <label className="search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Empresa, órgão, processo ou item…" /></label>
          <div className="operator"><div className="avatar">AF</div><div><strong>{authenticatedUser}</strong><span>Diretoria Institucional</span></div></div>
        </header>

        <section className="livebar">
          <div><span>{clock.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" })}</span><strong>{clock.toLocaleTimeString("pt-BR")}</strong></div>
          <div className="signals">
            <span className="green"><i></i><b>{stats.pipeline}</b> em acompanhamento</span>
            <span className="amber"><i></i><b>{stats.due}</b> repiques hoje</span>
            <span className="red"><i></i><b>{stats.overdue}</b> vencidos</span>
          </div>
          <div className="ticker">INTELIGÊNCIA QUE ACOMPANHA CADA OPORTUNIDADE • DECISÃO COM CONTEXTO • AÇÃO NO TEMPO CERTO</div>
        </section>

        <section className="hero-grid">
          <article className="hero-card">
            <div><p className="eyebrow">Janela homologada • 20 a 24 de julho</p><h2>{stats.total} oportunidades qualificadas</h2><p>O volume bruto desaparece. Ficam os fornecedores elegíveis, seus itens homologados e a rota comercial correta.</p></div>
            <div className="route-bars">
              <button className={route === "TODAS" ? "selected" : ""} onClick={() => setRoute("TODAS")}><span>Todas</span><b>{stats.total}</b></button>
              <button className={route.includes("Vazquez") ? "selected" : ""} onClick={() => setRoute("Corretora Vazquez & Fonseca")}><span>Corretora</span><b>{stats.vf}</b></button>
              <button className={route.includes("Vieira") ? "selected" : ""} onClick={() => setRoute("Consultoria Vieira Mendonca")}><span>Consultoria</span><b>{stats.vm}</b></button>
            </div>
          </article>
          <article className="focus-card"><span>PRIORIDADE COMERCIAL</span><strong>{brl(Math.max(...feed.opportunities.map((item) => item.valor_numero)))}</strong><p>Maior homologação da janela</p><div className="focus-line"></div><small>{operations.storage === "D1" ? "Banco online sincronizado" : "Conectando ao banco…"}</small></article>
        </section>

        <section className="metric-grid">
          <article><span>Oportunidades</span><strong>{stats.total}</strong><small>após todos os cortes</small></article>
          <article><span>Corretagem</span><strong>{stats.vf}</strong><small>acima de R$ 10 milhões</small></article>
          <article><span>Consultoria</span><strong>{stats.vm}</strong><small>de R$ 1 a 10 milhões</small></article>
          <article><span>Propostas</span><strong>{operations.proposals.length}</strong><small>registradas na nuvem</small></article>
        </section>

        <section className="table-card" id="oportunidades">
          <header><div><p className="eyebrow">Pipeline EVT-007</p><h2>Oportunidades em monitoramento</h2></div><span>{opportunities.length} resultados visíveis</span></header>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Tomador / item</th><th>Órgão e modalidade</th><th>Homologação</th><th>Garantia</th><th>Valor</th><th>Rota</th><th>Ação</th></tr></thead>
              <tbody>
                {opportunities.map((item, index) => {
                  const contact = normalize(operations.outreach[item.processo]);
                  return (
                    <tr key={`${item.processo}-${item.fornecedor_cnpj}-${index}`}>
                      <td><strong>{text(item.fornecedor)}</strong><span>{text(item.objeto)}</span><small>{item.fornecedor_cnpj}</small></td>
                      <td><strong>{text(item.orgao)}</strong><span>{text(item.modalidade)}</span><small>{item.processo}</small></td>
                      <td><strong>{item.data_homologacao}</strong><span>{item.evento}</span></td>
                      <td><span className={`guarantee ${item.garantia_execucao === "SIM" ? "yes" : ""}`}>{guaranteeLabel(item)}</span><small>{text(item.status)}</small></td>
                      <td className="money">{brl(item.valor_numero)}</td>
                      <td><span className={`route ${item.rota.includes("Vazquez") ? "broker" : "consulting"}`}>{item.rota.includes("Vazquez") ? "Corretora VF" : "Consultoria VM"}</span><small>{contact.status ? statuses.find(([key]) => key === contact.status)?.[1] : "Não iniciado"}</small></td>
                      <td><div className="actions"><button onClick={() => void open(item, "contact")}>Controlar</button><button onClick={() => void open(item, "email")}>E-mail</button><button onClick={() => void open(item, "proposal")}>Proposta</button><button onClick={() => void open(item, "documents")}>Editais</button></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
        <footer><span>VF Intelligence Platform • GSB Monitor</span><span>Dados que decidem. Oportunidades que transformam.</span></footer>
      </main>

      {selected && modal && (
        <div className="modal-layer" role="presentation">
          <button className="backdrop" aria-label="Fechar" onClick={() => setModal(null)} />
          <section className="dialog" role="dialog" aria-modal="true">
            <header><div><p className="eyebrow">{selected.processo}</p><h2>{modal === "contact" ? "Controle comercial" : modal === "email" ? "Abordagem institucional" : modal === "proposal" ? "Gerar proposta" : "Editais na nuvem"}</h2></div><button className="close" onClick={() => setModal(null)}>×</button></header>
            <div className="context"><strong>{text(selected.fornecedor)}</strong><span>{text(selected.orgao)} • {brl(selected.valor_numero)}</span></div>
            {modal === "contact" && <ContactForm form={form} setForm={setForm} onSave={() => saveContact()} />}
            {modal === "email" && <EmailForm opportunity={selected} form={form} setForm={setForm} onSent={registerSent} />}
            {modal === "proposal" && <ProposalForm opportunity={selected} decisionMaker={String(form.decision_maker ?? "")} onCreated={async () => { await refreshOperations(); setMessage("Proposta numerada e registrada."); }} />}
            {modal === "documents" && <DocumentList documents={cloudDocuments} />}
            {message && <p className="feedback">{message}</p>}
          </section>
        </div>
      )}
    </div>
  );
}

function DocumentList({ documents }: { documents: DocumentLink[] }) {
  return <div className="document-list">
    {documents.length ? documents.map((document) => (
      <a key={document.url} href={document.url} target="_blank" rel="noreferrer">
        <span>PDF</span><strong>{document.label}</strong><small>Abrir em nova guia</small>
      </a>
    )) : <div className="empty-state"><strong>Nenhum edital sincronizado para esta contratação.</strong><span>O arquivo aparecerá aqui após a próxima execução da ponte.</span></div>}
  </div>;
}

function ContactForm({ form, setForm, onSave }: { form: Outreach; setForm: (value: Outreach) => void; onSave: () => Promise<unknown> }) {
  return <div className="form">
    <label><span>Situação</span><select value={form.status ?? "NAO_INICIADO"} onChange={(event) => setForm({ ...form, status: event.target.value })}>{statuses.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    <label><span>Próximo repique</span><input type="date" value={String(form.next_follow_up_at ?? "")} onChange={(event) => setForm({ ...form, next_follow_up_at: event.target.value })} /></label>
    <label><span>Decisor</span><input value={String(form.decision_maker ?? "")} onChange={(event) => setForm({ ...form, decision_maker: event.target.value })} /></label>
    <label><span>E-mail</span><input type="email" value={String(form.email ?? "")} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
    <label><span>Telefone</span><input value={String(form.phone ?? "")} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
    <label className="wide"><span>Observações</span><textarea rows={5} value={String(form.notes ?? "")} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
    <div className="form-actions wide"><button className="primary" onClick={() => void onSave()}>Salvar no banco</button></div>
  </div>;
}

function EmailForm({ opportunity, form, setForm, onSent }: { opportunity: Opportunity; form: Outreach; setForm: (value: Outreach) => void; onSent: (subject: string, body: string) => Promise<void> }) {
  const draft = buildEmail(opportunity, String(form.decision_maker ?? ""));
  const [subject, setSubject] = useState(form.subject || draft.subject);
  const [body, setBody] = useState(form.body || draft.body);
  const copy = async () => navigator.clipboard.writeText(body);
  return <div className="form">
    <label><span>Decisor</span><input value={String(form.decision_maker ?? "")} onChange={(event) => setForm({ ...form, decision_maker: event.target.value })} /></label>
    <label><span>E-mail</span><input type="email" value={String(form.email ?? "")} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
    <label className="wide"><span>Assunto</span><input value={subject} onChange={(event) => setSubject(event.target.value)} /></label>
    <label className="wide"><span>Mensagem editável</span><textarea rows={14} value={body} onChange={(event) => setBody(event.target.value)} /></label>
    <div className="form-actions wide"><button onClick={() => void copy()}>Copiar mensagem</button><a className="button" href={`mailto:${form.email ?? ""}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`}>Abrir no e-mail</a><button className="primary" onClick={() => void onSent(subject, body)}>Registrar envio</button></div>
  </div>;
}

function ProposalForm({ opportunity, decisionMaker, onCreated }: { opportunity: Opportunity; decisionMaker: string; onCreated: () => Promise<void> }) {
  const suggested = Number(String(opportunity.percentual_garantia_execucao ?? "5").replace(/[^\d,.-]/g, "").replace(",", ".")) || 5;
  const [percentage, setPercentage] = useState(suggested);
  const [rate, setRate] = useState(0.75);
  const [months, setMonths] = useState(12);
  const insured = opportunity.valor_numero * percentage / 100;
  const premium = insured * rate / 100 * months / 12;
  const [result, setResult] = useState("");
  async function create() {
    const response = await fetch("/api/proposals", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        process_id: opportunity.processo,
        supplier: text(opportunity.fornecedor),
        supplier_cnpj: opportunity.fornecedor_cnpj,
        agency: text(opportunity.orgao),
        tender: text(opportunity.modalidade),
        decision_maker: decisionMaker,
        contract_value: opportunity.valor_numero,
        guarantee_percentage: percentage,
        annual_rate: rate,
        term_months: months,
      }),
    });
    const data = await response.json();
    if (!response.ok) return setResult(data.error ?? "Falha ao gerar.");
    setResult(`${data.proposal.number} criada — prêmio estimado ${brl(data.proposal.estimated_premium)}.`);
    await onCreated();
  }
  return <div className="form">
    <label><span>Percentual da garantia</span><input type="number" step="0.01" value={percentage} onChange={(event) => setPercentage(Number(event.target.value))} /></label>
    <label><span>Taxa anual (%)</span><input type="number" step="0.01" value={rate} onChange={(event) => setRate(Number(event.target.value))} /></label>
    <label><span>Prazo em meses</span><input type="number" value={months} onChange={(event) => setMonths(Number(event.target.value))} /></label>
    <div className="calculation"><span>Importância segurada</span><strong>{brl(insured)}</strong><span>Prêmio estimado</span><strong>{brl(premium)}</strong></div>
    <div className="form-actions wide"><button className="primary" onClick={() => void create()}>Numerar e registrar proposta</button></div>
    {result && <p className="feedback wide">{result}</p>}
  </div>;
}
