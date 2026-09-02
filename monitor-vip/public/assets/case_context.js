// E1: leitura operacional. Não carrega mocks nem motores futuros.
// case_id é o id JÁ PERSISTIDO de monitor.opportunities, tratado como opaco.
// A identidade canônica de ingestão será definida na Fase 2; não reconstruir ids.
export function esc(v) {
  return String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
}
export function known(v, empty = 'Não conhecido') {
  return v === null || v === undefined || String(v).trim() === '' ? empty : String(v);
}
export function brl(v) {
  if (v === null || v === undefined || v === '' || !Number.isFinite(Number(v))) return 'Não conhecido';
  return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v));
}
export function todayYmd() {
  return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
}
export async function getJson(url) {
  const response = await fetch(url, {cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(20000)});
  if (!response.ok) throw new Error(`Leitura indisponível (HTTP ${response.status}).`);
  return response.json();
}
export async function loadCaseContext() {
  const [feed, ops, session] = await Promise.allSettled([
    getJson('./api/feed'), getJson('./api/operations'), getJson('./api/auth/session')
  ]);
  if (feed.status !== 'fulfilled') throw new Error('Casos indisponíveis. Tente recarregar a página.');
  if (!Array.isArray(feed.value.opportunities) || feed.value.opportunities.some(i => !i.case_id)) {
    throw new Error('Identidade dos casos indisponível. Nenhum caso foi selecionado.');
  }
  return {
    feed:feed.value,
    operations:ops.status === 'fulfilled' ? ops.value : null,
    operationsError:ops.status !== 'fulfilled',
    user:session.status === 'fulfilled' ? session.value.user : null
  };
}
export function caseUrl(page, item) {
  return `./${page}?case_id=${encodeURIComponent(item.case_id)}`;
}
export function resolveCase(context, params) {
  const items = context.feed.opportunities;
  const id = params.get('case_id');
  if (id) {
    const matches = items.filter(i => i.case_id === id);
    return matches.length === 1 ? {status:'selected',item:matches[0]} : {status:'missing',items:[]};
  }
  const process = params.get('process');
  if (!process) return {status:'none',items};
  const matches = items.filter(i => i.processo === process);
  return matches.length === 1 ? {status:'selected',item:matches[0]} : {status:matches.length ? 'ambiguous':'missing',items:matches};
}
export function operationFor(context, item) {
  if (context.operationsError || !context.operations) return {status:'unavailable',record:null,proposals:[]};
  const record = context.operations.outreach?.[item.processo] || null;
  const proposals = (context.operations.proposals || []).filter(p => p.process_id === item.processo);
  const repeated = context.feed.opportunities.filter(i => i.processo === item.processo).length > 1;
  // Nunca atribuir a dois fornecedores um registro comercial indexado só por processo.
  if (repeated && (record || proposals.length)) return {status:'ambiguous',record:null,proposals:[]};
  return {status:record || proposals.length ? 'available':'empty',record,proposals};
}
export function operationProblem(op) {
  return op.status === 'unavailable' ? 'Memória operacional indisponível. Recarregue para consultar contato, notas e follow-up.'
    : op.status === 'ambiguous' ? 'Vínculo operacional a validar: este processo possui mais de um caso.' : '';
}
export function guaranteeOf(item) {
  // Texto herdado é uma observação do adaptador, NÃO uma cláusula verificada.
  // Não extrair 5 de "5% + reforço...", nem calcular obrigação a partir dele.
  return {original:known(item.percentual_garantia_execucao,'Não registrado'),
    status:'Não verificada no edital', value:null,
    source:'Registro operacional herdado; regra documental não verificada',
    confirmed:false};
}
export function statusLabel(status) {
  const labels = {NAO_INICIADO:'Não iniciado',EM_PREPARACAO:'Em preparação',PRONTO_PARA_ENVIO:'Pronto para envio',ENVIADO:'Enviado',AGUARDANDO_RETORNO:'Aguardando retorno',RESPONDEU:'Respondeu',PROPOSTA_EM_PREPARACAO:'Proposta em preparação',PROPOSTA_ENVIADA:'Proposta enviada',NEGOCIACAO:'Negociação',FECHADO:'Fechado',SEM_INTERESSE:'Sem interesse'};
  return labels[status] || known(status,'Não iniciado');
}
export function trackedItems(context) {
  if (context.operationsError) return [];
  return context.feed.opportunities.filter(item => {
    const op = operationFor(context,item), r = op.record;
    return op.status === 'available' && (op.proposals.length || (r && (
      (r.status && r.status !== 'NAO_INICIADO') || r.decision_maker || r.phone || r.email || r.notes || r.next_follow_up_at || r.subject || r.body || r.history?.length
    )));
  });
}
export function nextAction(op) {
  const problem = operationProblem(op);
  if (problem) return ['Consultar memória operacional', problem];
  const r = op.record;
  if (r?.next_follow_up_at) return ['Revisar follow-up',`Data registrada: ${r.next_follow_up_at}.`];
  if (r) return ['Revisar contato e notas','Definir o próximo passo a partir do registro existente.'];
  return ['Investigar o caso','A homologação, sozinha, não confirma uma dor comercial.'];
}
