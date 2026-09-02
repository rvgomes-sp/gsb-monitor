import {esc,known,loadCaseContext,resolveCase,getJson,caseUrl} from './case_context.js';
import {validateContract} from './case_contract.js';
import {shell,makeView,bindCommon,contactHistory,bindCaseStatus} from './dossier_view.js';

document.querySelector('#app').innerHTML=shell('investigation');
function render(contract,context,item){
 const v=makeView(contract,context,item),{field,fields,card,action,remaining}=v;
 const futureBlock=(key,kicker,title,prefix,ids,extra={})=>card({key,kicker,title,ids,more:remaining('investigation',prefix,ids),...extra});
 const event=['I0101','I0103','I0104','I0107','I0108','I0701'];
 const pains=['I1201','I1202','I1203','I1205','I1206','I1207'];
 const nav=[['company','Tomador'],['contracts','Carteira contratual'],['operational','Operacional'],['friction','Contratual'],['guarantee','Garantia & seguradora'],['signature','Assinatura'],['decision','Decisores'],['evidence','Evidências'],['attack','Plano de ação']];
 document.querySelector('#dossier-content').innerHTML=`
 <div class="case-heading"><div><span class="case-tag">CASO EM INVESTIGAÇÃO</span><h2>${esc(known(item?.fornecedor,'Selecione um caso'))}</h2></div><a class="outline-button" data-case-page="carteira_ana.html" href="./carteira_ana.html">Consultar na Carteira da Ana →</a></div>
 <section class="investigation-hero">
 ${card({key:'event',kicker:'01 · O que aconteceu',title:'Fato do evento',ids:event,more:remaining('investigation','01',event),kind:'event-card'})}
 ${card({key:'thesis',kicker:'02 · Tese inicial',title:'Por que investigar este caso?',ids:['I0201','I0204'],more:remaining('investigation','02',['I0201','I0204']),extra:'<p class="reading-note">A homologação é o fato de entrada. Ainda não confirma uma dor ou oportunidade comercial.</p>',kind:'thesis-card'})}
 ${card({key:'pain',kicker:'12 · Onde pode estar a dor?',title:'Mapa de possíveis dores',ids:pains,more:remaining('investigation','12',pains),actionId:'N013',actionLabel:'Ver todas as dores identificadas',reason:'Aguardando integração da Investigação',kind:'pain-card'})}
 </section>
 <section class="phase-strip"><span>FASES DA INVESTIGAÇÃO</span><ol>${['Fato','Hipótese','Investigação','Evidência','Dor','Tese','Intervenção'].map((s,i)=>`<li><b>${i+1}</b>${s}</li>`).join('')}</ol><small>Etapas previstas · progresso não registrado</small></section>
 <nav class="dossier-tabs" aria-label="Blocos da investigação"><a class="active" href="#event">Resumo do caso</a>${nav.map(([id,name])=>`<button type="button" data-detail-target="${id}">${name}</button>`).join('')}</nav>
 <div class="investigation-body"><section class="domain-grid">
 ${futureBlock('company','03 · Perfil do tomador','Empresa & histórico','03',['I0301','I0302','I0303','I0316'],{actionId:'N008',actionLabel:'Ver organograma',reason:'Aguardando integração OSINT'})}
 ${futureBlock('contracts','04 · Ciclo financeiro dos contratos','Carteira contratual','04',['I0402','I0403','I0404','I0405','I0406'],{extra:'<div class="capability-placeholder"><span>FLUXO DE CAIXA DOS CONTRATOS</span><strong>Aguardando integração</strong><small>Receita prevista · desembolso · exposição acumulada</small></div>'})}
 ${futureBlock('guarantee','07 / 08 · Garantia & seguradora','Compreender a obrigação','07/08',['I0701','I0710','I0804','I0805'],{extra:'<p class="reading-note">O texto de garantia é um registro herdado. A obrigação final depende da regra documental.</p>',actionId:'N011',actionLabel:'Ver análise seguradora',reason:'Aguardando integração seguradora'})}
 ${futureBlock('operational','05 · Pressão operacional','Estrutura para executar','05',['I0501','I0502','I0503'],{extra:'<div class="capability-placeholder map-placeholder"><span>MAPA OPERACIONAL</span><strong>Aguardando integração OSINT</strong><small>Sede · estrutura regional · execução</small></div>',actionId:'N009',actionLabel:'Ver mapa ampliado',reason:'Aguardando integração OSINT'})}
 ${futureBlock('friction','06 · Fricção contratual','Obrigações & condições','06',['I0601','I0602','I0603','I0608'],{actionId:'N010',actionLabel:'Ver matriz de riscos',reason:'Aguardando integração do Motor de Edital'})}
 ${futureBlock('decision','11 · Decisores & memória','Contato e notas reais','11',['I1101','I1102','I1103','I1104'],{extra:contactHistory(context,item),actionId:'N012',actionLabel:'Ver todos os decisores',reason:'Aguardando integração OSINT'})}
 ${futureBlock('signature','09 · Pressão de assinatura','O que falta para formalizar?','09',['I0907'])}
 ${futureBlock('evidence','Evidências · fontes e interpretação','O que sustenta a leitura','15',[],{extra:'<p class="reading-note">Registros do Monitor · camada canônica aguardando integração</p>'})}
 ${futureBlock('fiscal','10 · Fiscal · reservado','Integração futura','10',['I1001'],{kind:'reserved-card'})}
 </section><aside class="decision-rail">
 ${futureBlock('conclusion','13 · Tese final','Conclusão da investigação','13',['I1301','I1302','I1308'],{extra:'<button type="button" class="outline-button" data-detail-target="evidence">Ver registros e fontes →</button>'})}
 ${futureBlock('attack','14 · Plano de ataque','Da compreensão à ação','14',['I1401','I1402','I1403'],{actionId:'N015',actionLabel:'Iniciar abordagem',reason:'Ação ainda não integrada; nenhuma mensagem será enviada'})}
 </aside></div>
 <section class="case-output"><div><small>SAÍDA DO CASO</small>${field('I1309',{compact:true,source:false})}</div>${fields(['I0101','I1302','I1306','I1307'],{compact:true,source:false})}${action('N014','Gerar plano de abordagem','Aguardando integração da Investigação')}</section>
 <details class="identity-details"><summary>Identidade e referência do caso</summary><div class="field-grid">${fields(['I0001','I0002','I0003','I0004'])}</div></details>`;
 bindCommon(context,item,'investigacao_evt007.html');bindCaseStatus(context,item);
}
async function main(){
 const content=document.querySelector('#dossier-content');
 const [contractResult,contextResult]=await Promise.allSettled([getJson('./data/case_contract_v1_1.json').then(validateContract),loadCaseContext()]);
 if(contractResult.status!=='fulfilled'){content.innerHTML='<p role="alert">Contrato estrutural indisponível. Atualize a página para tentar novamente.</p>';return;}
 const context=contextResult.status==='fulfilled'?contextResult.value:null;
 const selected=context?resolveCase(context,new URLSearchParams(location.search)):null;
 render(contractResult.value,context,selected?.item);
 if(selected?.status==='ambiguous')document.querySelector('#live-status').textContent='Este processo tem mais de um caso. Selecione o fornecedor e a identidade correta.';
 if(selected?.status==='missing')document.querySelector('#live-status').textContent='Caso não encontrado. Selecione um registro existente.';
}
document.querySelector('#refresh').addEventListener('click',()=>location.reload());
main();
