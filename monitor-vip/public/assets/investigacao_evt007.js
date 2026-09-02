import {esc,known,brl,loadCaseContext,resolveCase,guaranteeOf,operationFor,operationProblem,caseUrl} from './case_context.js';
import {$,rows,memoryHtml,updateCaseLinks,renderPicker,showUser} from './case_view.js';

function evidence(item) {
  const source='Registro existente do Monitor';
  const list=[['Homologação informada',item.data_homologacao],['Valor homologado informado',item.valor_numero == null ? null : brl(item.valor_numero)]];
  const facts=list.map(([title,value])=>({kind:value?'confirmed':'unknown',title,detail:known(value),source}));
  const g=guaranteeOf(item);
  if (item.percentual_garantia_execucao) facts.push({kind:'indicative',title:'Observação herdada sobre garantia',detail:g.original,source:g.source});
  facts.push({kind:'unknown',title:'Obrigação de garantia',detail:'Não investigada no edital',source:'Leitura documental ainda não integrada'});
  return facts;
}
function evidenceHtml(facts) {
  return facts.map(f=>`<div class="evidence-item"><span class="evidence-marker ${f.kind}">${f.kind==='confirmed'?'✓':f.kind==='indicative'?'◐':'?'}</span><div><strong>${esc(f.title)}</strong><small>${esc(f.detail)}</small><small>Fonte: ${esc(f.source)}</small></div></div>`).join('');
}
function selectTab(name) {
  document.querySelectorAll('[data-tab]').forEach(el=>el.classList.toggle('active',el.dataset.tab===name));
  document.querySelectorAll('[data-panel]').forEach(el=>el.classList.toggle('active',el.dataset.panel===name));
}
function render(context,item) {
  $('#case-content').hidden=false;
  const g=guaranteeOf(item), op=operationFor(context,item), facts=evidence(item);
  $('#case-title').textContent=known(item.fornecedor);
  for (const [id,value] of Object.entries({company:item.fornecedor,agency:item.orgao,process:item.processo,object:item.objeto,date:item.data_homologacao,value:brl(item.valor_numero),guarantee:g.status,term:'Não investigado',cnpj:item.fornecedor_cnpj})) $('#event-'+id).textContent=known(value);
  $('#thesis-copy').textContent='A homologação é o fato de entrada. A dor e a tese comercial ainda não foram investigadas.';
  $('#pain-list').innerHTML='<p>? Dor comercial: não investigada.</p><p class="source-note">Não há conclusão registrada para este caso.</p>';
  $('#known-facts').innerHTML=evidenceHtml(facts);
  $('#evidence-table').innerHTML=evidenceHtml(facts);
  $('#open-questions').innerHTML=['Qual obrigação está efetivamente prevista nos documentos?','Há uma necessidade comercial comprovada?','Qual próximo passo faz sentido diante do contato e das notas existentes?'].map(q=>`<li>${q}</li>`).join('');
  $('#company-name').textContent=known(item.fornecedor);
  $('#company-profile').innerHTML=rows([['CNPJ',item.fornecedor_cnpj],['Órgão',item.orgao],['Processo',item.processo],['Rota registrada',item.rota],['Perfil ampliado','Não investigado']]);
  $('#guarantee-details').innerHTML=rows([['Estado',g.status],['Texto original preservado',g.original],['Origem',g.source],['Valor final da obrigação','Não conhecido'],['Prazo / coberturas','Não investigado']]);
  $('#insurer-view').innerHTML='<p>? Limite e condições da seguradora: não investigados.</p><p class="source-note">Capacidade futura. Nenhuma consulta seguradora foi executada.</p>';
  $('#decision-makers').innerHTML=memoryHtml(context,item);
  $('#operation-notice').textContent=operationProblem(op);
  $('#operation-notice').hidden=!operationProblem(op);
  $('#data-status').textContent=`Dados existentes do Monitor · ${known(context.feed.cloud?.updated_at)} · memória operacional ${context.operationsError?'indisponível':'consultada'}`;
  updateCaseLinks(item);
  document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>selectTab(button.dataset.tab)));
  $('#show-evidence').addEventListener('click',()=>selectTab('evidence'));
}
async function main() {
  try {
    const context=await loadCaseContext();
    showUser(context.user,'operator-');
    const resolved=resolveCase(context,new URLSearchParams(location.search));
    if(resolved.status==='selected') render(context,resolved.item);
    else {
      $('#data-status').textContent='Escolha um caso existente; nenhum registro foi criado.';
      const filter=renderPicker(context,resolved,'investigacao_evt007.html');
      $('#case-search').addEventListener('input',e=>filter(e.target.value));
    }
    if(resolved.status==='selected') {
      $('#case-search').addEventListener('input',e=>{
        if(!e.target.value.trim()) {$('#case-picker').hidden=true;return;}
        const filter=renderPicker(context,{status:'none',items:context.feed.opportunities},'investigacao_evt007.html');
        filter(e.target.value);
      });
    }
  } catch {
    $('#data-status').textContent='Casos indisponíveis. Recarregue para tentar novamente.';
    $('#case-picker').hidden=false;
    $('#case-picker').innerHTML='<p role="alert">Não foi possível ler os casos. Nenhum dado demonstrativo foi usado.</p><a href="./monitor_vip.html">Voltar ao Monitor</a>';
  }
}
main();
