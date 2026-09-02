import {esc,known,brl,caseUrl,operationFor} from './case_context.js';
import {STATUS,resolveField,fieldSource,portfolioMembership} from './case_contract.js';

const icons={home:'⌂',case:'◇',ana:'♡',clock:'◷',contact:'♧',file:'▤',map:'⌖',shield:'⬡',search:'⌕',arrow:'↗',refresh:'↻'};
export const icon=name=>`<span class="ui-icon" aria-hidden="true">${icons[name]||'◇'}</span>`;
export function shell(page){
 const ana=page==='ana';
 return `<aside class="dossier-sidebar"><a class="brand" href="./monitor_vip.html"><span class="brand-seal">GB</span><strong>GSB Monitor</strong><small>${ana?'VIP':'LICITAÇÃO ASSIMÉTRICA'}</small></a>${!ana?'<p class="brand-motto">Os fatos não mudam.<br>Muda a compreensão.</p>':''}
 <nav aria-label="Navegação principal"><a data-case-page="monitor_vip.html" href="./monitor_vip.html">${icon('home')}Monitor atual</a><a ${!ana?'aria-current="page"':''} data-case-page="investigacao_evt007.html" href="./investigacao_evt007.html">${icon('case')}Investigação EVT-007</a><a ${ana?'aria-current="page"':''} data-case-page="carteira_ana.html" href="./carteira_ana.html">${icon('ana')}Carteira da Ana</a>${ana?'<a href="#portfolio">◇ Casos da carteira</a><a href="#contacts">♧ Contatos</a><a href="#communication">▤ E-mails & conversas</a><a href="#agenda">◷ Follow-ups</a><a href="#proposals">▤ Propostas</a>':'<a href="#company">♧ Perfil do tomador</a><a href="#contracts">▤ Carteira contratual</a><a href="#guarantee">⬡ Garantia & seguradora</a><a href="#evidence">◇ Evidências</a>'}<div class="nav-reserved"><span>Monitor Fiscal <small>Futuro</small></span><span>Monitor Judicial <small>Futuro</small></span></div></nav>
 <div class="sidebar-end"><small>VF INTELLIGENCE PLATFORM</small><strong>${ana?'Relacionamento & ação':'Evidência antes da decisão'}</strong><p>Mesma identidade.<br>Memória preservada.</p></div></aside>
 <main class="dossier-main"><header class="dossier-header"><div><p class="eyebrow">${ana?'RELACIONAMENTO · OPERAÇÃO':'EVT-007 · HOMOLOGAÇÃO'}</p><h1>${ana?'Carteira da Ana':'Investigação EVT-007'}</h1><p>${ana?'Gestão de oportunidades, relacionamento e follow-up.':'Compreender o caso antes de definir a intervenção.'}</p></div><div class="header-tools"><label class="case-search">${icon('search')}<input id="case-search" type="search" aria-label="Buscar caso no Monitor" placeholder="Buscar empresa, órgão, CNPJ..."></label><button id="refresh" class="outline-button" type="button">${icon('refresh')}Atualizar dados</button><span class="user-chip" id="user-chip">Perfil em consulta</span></div></header>
 ${ana?'<section class="ana-quote"><span>“…Mas é Deus quem dá a última palavra.”</span><small>Provérbios 16:1</small></section>':''}
 <div id="live-status" class="live-status" role="status">Consultando os registros existentes…</div><section id="case-picker" class="dossier-card" hidden></section><div id="dossier-content" aria-busy="true"></div><footer class="dossier-footer"><span>GSB · Licitação Assimétrica</span><span>Fatos, fontes e memória do mesmo caso.</span></footer></main>`;
}
export function makeView(contract,context,item){
 const map=new Map(contract.fields.map(f=>[f.id,f]));
 const field=(id,{label,compact=false,source=true}={})=>{
  const f=map.get(id);if(!f)throw new Error('Campo fora do contrato: '+id);
  const v=resolveField(f,context,item);if(v.hidden)return '';
  const marker=v.status===STATUS.real?(f.type==='INDÍCIO'?'◐':'✓'):v.status===STATUS.error?'!':'?';
  return `<div class="contract-field ${compact?'compact':''} state-${v.status}" data-contract-id="${id}" data-implementation-status="${v.status}"><span class="field-label">${esc(label||f.label)}</span><strong><i aria-hidden="true">${marker}</i>${esc(v.value)}</strong>${source?`<details class="field-source"><summary aria-label="Fonte de ${esc(label||f.label)}">Fonte e significado</summary><p>${esc(fieldSource(f,item))}</p><p>${esc(f.definition)}</p>${v.status===STATUS.future?'<p>Capacidade ainda não integrada.</p>':''}</details>`:''}</div>`;
 };
 const fields=(ids,opts)=>ids.map(id=>field(id,opts)).join('');
 const action=(id,label,reason)=>`<div class="future-action" data-contract-id="${id}" data-implementation-status="${map.get(id)?.status||STATUS.future}"><button class="outline-button" type="button" disabled aria-disabled="true">${esc(label||map.get(id)?.label||'Capacidade futura')} <span aria-hidden="true">→</span></button><small>${esc(reason||'Aguardando integração')}</small></div>`;
 const card=({key,kicker,title,ids=[],more=[],extra='',actionId,actionLabel,reason,kind=''})=>`<article class="dossier-card ${kind}" id="${key}" data-section="${key}"><header><span class="section-kicker">${esc(kicker)}</span><h2>${esc(title)}</h2></header><div class="field-grid">${fields(ids)}</div>${extra}${more.length?`<details class="block-details"><summary>Ver detalhes do bloco <span>＋</span></summary><div class="field-grid">${fields(more)}</div></details>`:''}${actionId?action(actionId,actionLabel,reason):''}</article>`;
 const group=(screen,prefix)=>contract.fields.filter(f=>f.screen===screen&&f.block.startsWith(prefix)).map(f=>f.id);
 const remaining=(screen,prefix,ids)=>group(screen,prefix).filter(id=>!ids.includes(id));
 return {map,field,fields,action,card,group,remaining};
}
export function bindCommon(context,item,page){
 document.querySelectorAll('[data-case-page]').forEach(a=>{if(item)a.href=caseUrl(a.dataset.casePage,item);});
 if(item)history.replaceState(null,'',`?case_id=${encodeURIComponent(item.case_id)}`);
 const user=document.querySelector('#user-chip');user.textContent=known(context?.user?.name,'Perfil indisponível');
 const search=document.querySelector('#case-search'),picker=document.querySelector('#case-picker');
 const show=query=>{
  picker.hidden=false;
  const result=(context?.feed?.opportunities||[]).filter(i=>[i.fornecedor,i.fornecedor_cnpj,i.orgao,i.processo].join(' ').toLowerCase().includes(query.toLowerCase()));
  picker.innerHTML=`<h2>Consultar caso do Monitor</h2><p>Consultar não atribui o caso à Carteira da Ana.</p><div class="picker-results">${result.length?result.map(i=>`<a href="${esc(caseUrl(page,i))}"><strong>${esc(i.fornecedor)}</strong><span>${esc(i.fornecedor_cnpj)} · ${esc(i.processo)}</span></a>`).join(''):'Nenhum caso encontrado.'}</div>`;
 };
 search.addEventListener('input',e=>{if(!e.target.value.trim()&&item){picker.hidden=true;return;}show(e.target.value);});
 if(!item&&context?.feed)show('');
 document.querySelector('#dossier-content').setAttribute('aria-busy','false');
 document.querySelectorAll('[data-detail-target]').forEach(button=>button.addEventListener('click',()=>{
  const target=document.getElementById(button.dataset.detailTarget);if(!target)return;
  const more=target.querySelector('.block-details');if(more)more.open=true;
  target.scrollIntoView({behavior:'smooth',block:'start'});
  document.querySelectorAll('[data-detail-target]').forEach(b=>b.classList.toggle('active',b===button));
 }));
}
export function contactHistory(context,item){
 if(!context||!item)return '<p class="quiet">Selecione um caso para consultar a memória existente.</p>';
 const op=operationFor(context,item);
 if(['unavailable','ambiguous'].includes(op.status))return '<p class="inline-alert">Memória operacional indisponível ou vínculo a validar.</p>';
 const list=op.record?.history||[];
 return `<details class="block-details"><summary>Histórico operacional <span>${list.length}</span></summary>${list.map(h=>`<p class="history-item"><strong>${esc(known(h.event))}</strong><span>${esc(known(h.at))} · ${esc(known(h.operator))}</span></p>`).join('')||'<p>Nenhum histórico registrado.</p>'}</details>`;
}
export function bindCaseStatus(context,item){
 const status=document.querySelector('#live-status');
 if(!context){status.classList.add('error');status.textContent='Leitura indisponível. Use Atualizar dados para tentar novamente.';return;}
 status.classList.toggle('error',context.operationsError);
 status.textContent=context.operationsError?'Dados do caso consultados · memória operacional indisponível':item?'Registro existente do Monitor · memória operacional consultada':'Escolha um caso do Monitor para investigar.';
}
