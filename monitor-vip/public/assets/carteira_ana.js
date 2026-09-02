import {esc,known,loadCaseContext,resolveCase,getJson,caseUrl,operationFor} from './case_context.js';
import {validateContract,portfolioMembership,STATUS} from './case_contract.js';
import {shell,makeView,bindCommon,contactHistory,bindCaseStatus,icon} from './dossier_view.js';

document.querySelector('#app').innerHTML=shell('ana');
function render(contract,context,item){
 const {field,fields,card,action,remaining}=makeView(contract,context,item);
 const block=(key,kicker,title,prefix,ids,extra={})=>card({key,kicker,title,ids,more:remaining('ana',prefix,ids),...extra});
 const membership=portfolioMembership();
 const operation=context&&item?operationFor(context,item):null;
 const proposalUnavailable=!context||context.operationsError||['unavailable','ambiguous'].includes(operation?.status);
 document.querySelector('#dossier-content').innerHTML=`
 <section class="ana-kpis" aria-label="Indicadores previstos"><article>${icon('case')}${field('A0101',{label:'Casos prioritários',source:false})}</article><article>${icon('clock')}${field('A0103',{label:'Aguardando retorno',source:false})}</article><article>${icon('file')}${field('A0104',{label:'Propostas em revisão',source:false})}</article><article>${icon('clock')}${field('A0105',{label:'Follow-ups hoje',source:false})}</article><article>${icon('clock')}${field('A0102',{label:'Janela crítica',source:false})}</article></section>
 <p class="kpi-caption">Retornos e follow-ups refletem os registros operacionais existentes do Monitor. A atribuição à Carteira da Ana ainda não está estruturada.</p>
 <section class="ana-primary-grid">
 <article class="dossier-card portfolio-card" id="portfolio"><header><span class="section-kicker">O que merece sua atenção agora</span><h2>Casos da carteira</h2></header><div class="portfolio-columns"><span>Caso</span><span>Dor principal</span><span>Urgência</span><span>Próxima ação</span></div><div class="portfolio-empty" data-contract-id="A0214" data-implementation-status="${STATUS.future}"><span class="empty-icon">◇</span><h3>Atribuição de casos ainda não estruturada</h3><p>A carteira receberá os casos deliberadamente atribuídos. Consultar um caso não cria esse vínculo.</p></div>
 ${item?`<section class="consultation-case"><small>CASO EM CONSULTA · NÃO ATRIBUÍDO</small><h3>${esc(item.fornecedor)}</h3><p>${esc(item.orgao)}</p><div class="field-grid">${fields(['A0206','A0208','A0209','A0212'],{source:false})}</div><a class="outline-button" data-case-page="investigacao_evt007.html" href="./investigacao_evt007.html">Abrir Investigação →</a></section>`:'<p class="reading-note">Use a busca para consultar um dos casos reais do Monitor.</p>'}
 <details class="block-details"><summary>Estrutura dos casos da carteira <span>＋</span></summary><div class="field-grid">${fields(remaining('ana','02',['A0214']))}</div></details></article>
 ${block('selected','Caso selecionado',known(item?.fornecedor,'Selecione um caso'),'03',['A0312','A0302','A0303','A0313','A0306','A0307','A0309'],{extra:`<p class="assignment-note">${item?membership.text:'Consulte um caso do Monitor'}</p><a class="primary-button" data-case-page="investigacao_evt007.html" href="./investigacao_evt007.html">Ver detalhes completos do caso →</a>`})}
 </section>
 <section class="ana-bottom-grid">
 ${block('contacts','Contatos & relacionamento','Memória de quem já foi contatado','04',['A0401','A0403','A0404','A0406'],{extra:contactHistory(context,item),actionId:'N019',actionLabel:'Adicionar contato',reason:'Indisponível nesta fase · vínculo do caso em revisão'})}
 ${block('communication','E-mails & conversas','Comunicação registrada','05',['A0501','A0502','A0503','A0504'],{extra:`<div class="action-pair">${action('N021','Ver conversa','Aguardando integração')}${action('N022','Preparar novo e-mail','Indisponível nesta fase')}</div>${action('N023','Registrar ligação','Indisponível nesta fase · nenhuma gravação')}`})}
 ${block('agenda','Próximos follow-ups','Agenda operacional','06',['A0601','A0602','A0603','A0606'],{actionId:'N024',actionLabel:'Ver agenda completa',reason:'Aguardando integração da agenda'})}
 </section>
 <section class="ana-support-grid">
 ${card({key:'next-action',kicker:'Próxima melhor ação',title:'O próximo passo precisa de fundamento',ids:['A0310','A0311','A0308'],extra:'<p class="reading-note">Recomendação analítica ainda não integrada. A decisão de abordar permanece humana.</p>',actionId:'N014',actionLabel:'Gerar plano de abordagem',reason:'Aguardando integração da Investigação'})}
 ${block('proposals','Propostas','Propostas registradas','07',[],{extra:`<p class="proposal-empty" data-implementation-status="${proposalUnavailable?STATUS.error:operation?.proposals.length?STATUS.real:STATUS.empty}">${proposalUnavailable?'Leitura de propostas indisponível':!item?'Selecione um caso para consultar propostas.':operation?.proposals.length?'Consulte os registros nos detalhes abaixo.':'Nenhuma proposta registrada para este caso.'}</p>`,actionId:'N026',actionLabel:'Gerar proposta',reason:'Indisponível nesta fase · nenhuma nova gravação'})}
 </section>
 <details class="dossier-card history-details"><summary>Histórico e autoria dos registros</summary><div class="field-grid">${fields(remaining('ana','08',[]))}</div></details>`;
 bindCommon(context,item,'carteira_ana.html');bindCaseStatus(context,item);
}
async function main(){
 const results=await Promise.allSettled([getJson('./data/case_contract_v1_1.json').then(validateContract),loadCaseContext()]);
 if(results[0].status!=='fulfilled'){document.querySelector('#dossier-content').innerHTML='<p role="alert">Contrato estrutural indisponível. Atualize a página.</p>';return;}
 const context=results[1].status==='fulfilled'?results[1].value:null;
 const selected=context?resolveCase(context,new URLSearchParams(location.search)):null;
 render(results[0].value,context,selected?.item);
 if(selected?.status==='ambiguous')document.querySelector('#live-status').textContent='Processo com mais de um caso. Escolha a identidade correta; nenhum vínculo comercial será presumido.';
 if(selected?.status==='missing')document.querySelector('#live-status').textContent='Caso não encontrado. Selecione um registro existente.';
}
document.querySelector('#refresh').addEventListener('click',()=>location.reload());
main();
