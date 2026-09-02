import assert from 'node:assert/strict';
import test from 'node:test';
import {resolveCase,caseUrl,operationFor,operationProblem,guaranteeOf,trackedItems,loadCaseContext,brl} from '../public/assets/case_context.js';

// Dados sintéticos somente neste teste; jamais enviados ao banco ou à UI operacional.
const first={case_id:'persisted-a',processo:'same-process',fornecedor_cnpj:'111',fornecedor:'Empresa A'};
const second={case_id:'persisted-b',processo:'same-process',fornecedor_cnpj:'222',fornecedor:'Empresa B'};
const unique={case_id:'persisted-c',processo:'unique-process',fornecedor:'Empresa C'};
const context={feed:{opportunities:[first,second,unique]},operations:{outreach:{},proposals:[]},operationsError:false};

test('id persistido seleciona fornecedor exato; processo repetido exige escolha',()=>{
  assert.equal(resolveCase(context,new URLSearchParams({case_id:'persisted-b'})).item,second);
  assert.equal(resolveCase(context,new URLSearchParams({process:'same-process'})).status,'ambiguous');
  assert.equal(resolveCase(context,new URLSearchParams({process:'unique-process'})).item,unique);
});
test('id inválido não seleciona outro caso nem cai no primeiro',()=>{
  assert.equal(resolveCase(context,new URLSearchParams({case_id:'missing',process:'unique-process'})).status,'missing');
  assert.equal(resolveCase(context,new URLSearchParams()).status,'none');
});
test('navegação preserva id opaco com caracteres reservados',()=>{
  const item={...first,case_id:'contrato/L1|cnpj|0'};
  const path=caseUrl('carteira_ana.html',item);
  assert.equal(new URL(path,'https://example.test').searchParams.get('case_id'),item.case_id);
});
test('contato comercial não é atribuído a dois fornecedores do mesmo processo',()=>{
  const ctx={...context,operations:{outreach:{'same-process':{notes:'registro do processo'}},proposals:[]}};
  for(const item of [first,second]) {
    const op=operationFor(ctx,item);
    assert.equal(op.status,'ambiguous');assert.equal(op.record,null);
  }
});
test('contato, notas e histórico pertencem ao caso único sem criar cópia',()=>{
  const record={status:'EM_PREPARACAO',decision_maker:'Contato de teste',notes:'Nota de teste',history:[{event:'atualização'}],next_follow_up_at:''};
  const ctx={...context,operations:{outreach:{'unique-process':record},proposals:[]}};
  assert.equal(operationFor(ctx,unique).record,record);
  assert.deepEqual(trackedItems(ctx),[unique]);
  assert.equal(operationFor(ctx,first).status,'empty');
});
test('carteira vazia não é preenchida com casos arbitrários',()=>{
  assert.deepEqual(trackedItems(context),[]);
});
test('indisponível difere de vazio e nunca produz memória fictícia',()=>{
  const ctx={...context,operations:null,operationsError:true};
  assert.equal(operationFor(ctx,unique).status,'unavailable');
  assert.match(operationProblem(operationFor(ctx,unique)),/indisponível/);
  assert.equal(operationFor(context,unique).status,'empty');
});
test('expressão composta e percentuais simples herdados não viram obrigação confirmada',()=>{
  for(const original of ['5% + reforço (deságio 19%)','5%','condicionada à assinatura']) {
    const result=guaranteeOf({percentual_garantia_execucao:original,valor_numero:187770000});
    assert.equal(result.original,original);assert.equal(result.value,null);assert.equal(result.confirmed,false);
  }
});
test('ausência monetária não é zero; zero real continua zero',()=>{
  assert.equal(brl(null),'Não conhecido');assert.equal(brl(''),'Não conhecido');assert.match(brl(0),/0,00/);
});
test('falha de operations conserva feed mas não usa mocks ou arrays fictícios',async t=>{
  const calls=[];
  t.mock.method(globalThis,'fetch',async url=>{
    calls.push(url);
    if(url==='./api/feed')return Response.json(context.feed);
    if(url==='./api/operations')return new Response('',{status:503});
    if(url==='./api/auth/session')return Response.json({user:{name:'Teste'}});
    throw new Error('Fonte inesperada');
  });
  const result=await loadCaseContext();
  assert.equal(result.operations,null);assert.equal(result.operationsError,true);
  assert.equal(result.feed.opportunities.length,3);
  assert.deepEqual(calls.sort(),['./api/auth/session','./api/feed','./api/operations']);
});
test('falha no feed encerra leitura sem recorrer à safra estática antiga',async t=>{
  const calls=[];
  t.mock.method(globalThis,'fetch',async url=>{calls.push(url);return new Response('',{status:503});});
  await assert.rejects(loadCaseContext(),/Casos indisponíveis/);
  assert.ok(calls.every(url=>url.startsWith('./api/')));
});
