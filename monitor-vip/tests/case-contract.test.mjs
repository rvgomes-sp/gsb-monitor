import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateContract,resolveField,portfolioMembership,STATUS} from '../public/assets/case_contract.js';

const contract=validateContract(JSON.parse(await readFile(new URL('../public/data/case_contract_v1_1.json',import.meta.url),'utf8')));
const field=id=>contract.fields.find(f=>f.id===id);
// Dados artificiais restritos aos testes; nunca enviados ao Monitor.
const item={case_id:'case-a',processo:'process-a',fornecedor:'Caso de teste',valor_numero:20000000,percentual_garantia_execucao:'5% + reforço (deságio 19%)'};
const record={decision_maker:'Contato de teste',notes:'Nota preservada',email:'',next_follow_up_at:'',history:[]};
const ctx={feed:{opportunities:[item]},operations:{outreach:{'process-a':record},proposals:[]},operationsError:false};

test('contrato congelado conserva as 284 identidades e distribuição',()=>{
 assert.deepEqual(['investigation','ana','actions'].map(s=>contract.fields.filter(f=>f.screen===s).length),[176,72,36]);
 assert.throws(()=>validateContract({...contract,sha256:'outro'}));
});
test('real exibe valor, vazio explícito não vira zero',()=>{
 assert.equal(resolveField(field('I1101'),ctx,item).value,record.decision_maker);
 assert.equal(resolveField(field('I1103'),ctx,item).status,STATUS.empty);
 assert.equal(resolveField(field('A0601'),ctx,item).value,'Follow-up ainda não definido');
 assert.equal(resolveField(field('I0108'),ctx,{...item,valor_numero:null}).status,STATUS.empty);
 assert.equal(resolveField(field('I0108'),ctx,{...item,valor_numero:0}).status,STATUS.real);
});
test('erro de memória e ambiguidade prevalecem sobre vazio ou números',()=>{
 const failed={...ctx,operations:null,operationsError:true};
 assert.equal(resolveField(field('I1101'),failed,item).status,STATUS.error);
 assert.equal(resolveField(field('A0103'),failed,item).value,'Indisponível');
 const ambiguous={...ctx,feed:{opportunities:[item,{...item,case_id:'case-b'}]}};
 assert.equal(resolveField(field('I1101'),ambiguous,item).status,STATUS.error);
 assert.equal(resolveField(field('A0103'),ambiguous,item).status,STATUS.error);
});
test('futuro preserva espaço mas não produz cálculo ou probabilidade',()=>{
 for(const id of ['I0804','I0806','I0204','A0101','A0104'])assert.equal(resolveField(field(id),ctx,item).status,STATUS.future);
 assert.equal(resolveField(field('I0710'),ctx,item).value,'A confirmar pela regra documental');
});
test('conteúdo demonstrativo é omitido independentemente do valor disponível',()=>{
 assert.equal(resolveField({...field('I0108'),status:STATUS.demo},ctx,item).hidden,true);
});
test('garantia composta inteira e memória única atravessam as representações',()=>{
 assert.equal(resolveField(field('I0701'),ctx,item).value,item.percentual_garantia_execucao);
 assert.equal(resolveField(field('A0313'),ctx,item).value,item.percentual_garantia_execucao);
 assert.equal(resolveField(field('A0406'),ctx,item).value,resolveField(field('I1104'),ctx,item).value);
});
test('contato e abertura de caso não criam atribuição à Carteira',()=>{
 assert.equal(portfolioMembership(ctx,item).assigned,false);
 assert.equal(portfolioMembership(ctx,item).status,STATUS.future);
});
test('novas visões não incluem chamadas de escrita nem fontes demonstrativas',async()=>{
 for(const file of ['investigacao_evt007.js','carteira_ana.js','dossier_view.js','case_contract.js']){
  const src=await readFile(new URL('../public/assets/'+file,import.meta.url),'utf8');
  assert.doesNotMatch(src,/method\s*:\s*['"](?:POST|PUT|PATCH|DELETE)|commercial_intelligence_cases\.json|evt007_assimetrica\.js|localStorage\.setItem/);
 }
 const src=await readFile(new URL('../public/assets/dossier_view.js',import.meta.url),'utf8');
 assert.match(src,/disabled aria-disabled="true"/);
});
