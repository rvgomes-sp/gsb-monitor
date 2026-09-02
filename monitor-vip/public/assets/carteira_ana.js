import {esc,known,brl,todayYmd,loadCaseContext,resolveCase,caseUrl,operationFor,operationProblem,statusLabel,trackedItems,nextAction,guaranteeOf} from './case_context.js';
import {$,rows,memoryHtml,proposalHtml,updateCaseLinks,renderPicker,showUser} from './case_view.js';

function renderList(context,items,selected,query='') {
  const filtered=items.filter(i=>[i.fornecedor,i.fornecedor_cnpj,i.orgao,i.processo,operationFor(context,i).record?.decision_maker].join(' ').toLowerCase().includes(query.toLowerCase()));
  $('#ana-case-count').textContent=context.operationsError?'Leitura indisponível':`${filtered.length} casos com registro operacional`;
  $('#ana-case-list').innerHTML=context.operationsError ? '<p role="status">Não foi possível consultar a carteira. Recarregue para tentar novamente.</p>' : filtered.length ? filtered.map(item=>`<div class="ana-case ${selected?.case_id===item.case_id?'active':''}"><div><h3>${esc(item.fornecedor)}</h3><p>${esc(item.orgao)} · ${esc(item.fornecedor_cnpj)}</p><p>${esc(item.processo)}</p></div><div class="metric"><span>Valor homologado</span><strong>${esc(brl(item.valor_numero))}</strong></div><div class="metric"><span>Estado registrado</span><strong>${esc(statusLabel(operationFor(context,item).record?.status))}</strong></div><a class="case-open" href="${esc(caseUrl('carteira_ana.html',item))}">Abrir caso</a></div>`).join('') : '<p>Nenhum caso com registro operacional encontrado.</p>';
}
function renderKpis(context,items) {
  if(context.operationsError) {
    for(const id of ['priority','waiting','proposals','followups']) $('#ana-'+id).textContent='Indisponível';
    return;
  }
  const records=items.map(i=>operationFor(context,i).record||{});
  $('#ana-priority').textContent=items.length;
  $('#ana-waiting').textContent=records.filter(r=>r.status==='AGUARDANDO_RETORNO').length;
  $('#ana-proposals').textContent=(context.operations.proposals||[]).length;
  $('#ana-followups').textContent=records.filter(r=>r.next_follow_up_at?.slice(0,10)===todayYmd()).length;
}
function renderSelected(context,item) {
  $('#selected-case-content').hidden=false;
  $('#case-memory-content').hidden=false;
  const op=operationFor(context,item),problem=operationProblem(op),r=op.record||{};
  $('#selected-company').textContent=known(item.fornecedor);
  $('#selected-status').textContent=problem ? 'Leitura pendente' : statusLabel(r.status);
  $('#selected-summary').innerHTML=rows([['CNPJ',item.fornecedor_cnpj],['Processo',item.processo],['Órgão',item.orgao],['Valor homologado',brl(item.valor_numero)],['Garantia',guaranteeOf(item).status],['Dor comercial','Não investigada'],['Follow-up',problem?'Indisponível':known(r.next_follow_up_at,'Ainda não definido')],['Rota registrada',item.rota]]);
  const [action,explanation]=nextAction(op);
  $('#selected-next-action').textContent=action;
  $('#selected-next-copy').textContent=explanation;
  $('#ana-contacts').innerHTML=memoryHtml(context,item);
  $('#ana-email-summary').innerHTML=problem ? `<p>${esc(problem)}</p>` : r.subject || r.body ? `<small>Texto registrado no controle comercial; não comprova envio.</small><strong>${esc(known(r.subject,'Sem assunto registrado'))}</strong><p class="preserved-text">${esc(known(r.body,'Sem mensagem registrada'))}</p>` : '<p>Nenhuma mensagem registrada.</p>';
  $('#ana-followup-list').innerHTML=problem ? `<p>${esc(problem)}</p>` : `<p>Follow-up: ${esc(known(r.next_follow_up_at,'ainda não definido'))}</p>`;
  $('#ana-proposal-list').innerHTML=proposalHtml(op);
  $('#operation-notice').hidden=!problem;
  $('#operation-notice').textContent=problem;
  $('#case-not-tracked').hidden=op.status!=='empty';
  updateCaseLinks(item);
}
async function main() {
  try {
    const context=await loadCaseContext(), items=trackedItems(context), resolved=resolveCase(context,new URLSearchParams(location.search));
    showUser(context.user,'ana-');
    renderKpis(context,items);
    renderList(context,items,resolved.item);
    if(resolved.status==='selected') renderSelected(context,resolved.item);
    else if(resolved.status==='ambiguous'||resolved.status==='missing') renderPicker(context,resolved,'carteira_ana.html');
    $('#ana-search').addEventListener('input',e=>renderList(context,items,resolved.item,e.target.value));
    $('#ana-data-status').textContent=context.operationsError?'Memória operacional indisponível; os dados comerciais não foram substituídos por exemplos.':'Fonte: registros existentes do Monitor e memória operacional consultada.';
  } catch {
    $('#ana-data-status').textContent='Casos indisponíveis. Recarregue para tentar novamente.';
    $('#case-picker').hidden=false;
    $('#case-picker').innerHTML='<p role="alert">Não foi possível ler os casos. Nenhum dado demonstrativo foi usado.</p><a href="./monitor_vip.html">Voltar ao Monitor</a>';
  }
}
main();
