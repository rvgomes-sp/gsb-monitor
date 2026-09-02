import {esc,known,brl,caseUrl,operationFor,operationProblem,statusLabel} from './case_context.js';
export const $ = s => document.querySelector(s);
export function rows(values) {
  return values.map(([label,value])=>`<div class="row"><span>${esc(label)}</span><strong>${esc(known(value))}</strong></div>`).join('');
}
export function memoryHtml(context,item) {
  const op = operationFor(context,item), problem = operationProblem(op);
  if (problem) return `<p class="case-warning" role="status">${esc(problem)}</p>`;
  const r = op.record || {};
  const history = r.history || [];
  return `<p class="source-note">Fonte: registros operacionais existentes do caso.</p>
    <div class="selected-summary">${rows([
      ['Situação',statusLabel(r.status)],['Contato',known(r.decision_maker,'Não identificado')],
      ['Telefone',r.phone],['E-mail',r.email],['Follow-up',known(r.next_follow_up_at,'Ainda não definido')]
    ])}</div>
    <h3>Notas registradas</h3><p class="preserved-text">${esc(known(r.notes,'Nenhuma nota registrada'))}</p>
    <details><summary>Histórico registrado (${history.length})</summary>${history.length ? history.map(h=>`<p>${esc(known(h.at))} · ${esc(known(h.event))} · ${esc(statusLabel(h.status))}<br><small>${esc(known(h.operator))}</small></p>`).join('') : '<p>Nenhum histórico registrado.</p>'}</details>`;
}
export function proposalHtml(op) {
  const problem = operationProblem(op);
  if (problem) return `<p>${esc(problem)}</p>`;
  return op.proposals.length ? op.proposals.map(p=>`<p><strong>${esc(p.number)}</strong> · ${esc(p.status)}<br>Valor registrado: ${esc(brl(p.contract_value))}</p>`).join('') : '<p>Nenhuma proposta registrada.</p>';
}
export function updateCaseLinks(item) {
  document.querySelectorAll('a[data-case-page]').forEach(a=>{
    a.href=caseUrl(a.dataset.casePage,item);
  });
  history.replaceState(null,'',`?case_id=${encodeURIComponent(item.case_id)}`);
}
export function renderPicker(context,resolved,page) {
  const panel = $('#case-picker');
  panel.hidden = false;
  const title = resolved.status === 'ambiguous' ? 'Este processo possui mais de um caso. Escolha o fornecedor.' : resolved.status === 'missing' ? 'Caso não encontrado. Selecione um registro existente.' : 'Selecione um caso';
  panel.innerHTML=`<h2>${title}</h2><div id="case-picker-list"></div>`;
  const candidates = resolved.status === 'missing' ? context.feed.opportunities : resolved.items;
  const render = query => {
    const list=candidates.filter(i=>[i.fornecedor,i.fornecedor_cnpj,i.orgao,i.processo].join(' ').toLowerCase().includes(query.toLowerCase()));
    $('#case-picker-list').innerHTML=list.length ? list.map(i=>`<p><a class="primary-link" href="${esc(caseUrl(page,i))}">${esc(i.fornecedor)} · ${esc(i.fornecedor_cnpj)} · ${esc(i.processo)}</a></p>`).join('') : '<p>Nenhum caso encontrado.</p>';
  };
  render('');
  return render;
}
export function showUser(user,prefix) {
  $(`#${prefix}name`).textContent=known(user?.name,'Usuário autenticado');
  $(`#${prefix}role`).textContent=known(user?.role,'Perfil indisponível');
  $(`#${prefix}initials`).textContent=known(user?.initials,'—');
}
