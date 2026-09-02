import {brl,operationFor,known,todayYmd} from './case_context.js';

export const STATUS=Object.freeze({real:'REAL_FUNCIONAL',empty:'REAL_SEM_REGISTRO_NESTE_CASO',future:'PREVISTO_NAO_INTEGRADO',demo:'DEMONSTRATIVO_NAO_OPERACIONAL',error:'INDISPONIVEL_ERRO'});
export const CONTRACT_SHA='c9523412762e122d0df6a056f11b71d4d6c544601c354a8e7b20889414e1c6bf';
const present=v=>v!==undefined&&v!==null&&v!==''&&!(Array.isArray(v)&&!v.length);
export function validateContract(contract){
 if(contract.sha256!==CONTRACT_SHA||contract.version!=='1.1'||contract.fields.length!==284||new Set(contract.fields.map(f=>f.id)).size!==284)throw new Error('Contrato estrutural indisponível');
 if(contract.fields.some(f=>!Object.values(STATUS).includes(f.status)))throw new Error('Estado do contrato inválido');
 return contract;
}
export function portfolioMembership(){
 // O contrato canônico exige atribuição deliberada. Não há fonte integrada para ela.
 return {status:STATUS.future,assigned:false,text:'Caso ainda não atribuído à Carteira da Ana'};
}
function statistic(field,context){
 if(context.operationsError||!context.operations)return {status:STATUS.error,value:'Indisponível'};
 const entries=Object.entries(context.operations.outreach||{});
 // Um registro por processo não pode ser contado como dois casos.
 if(entries.some(([process])=>context.feed.opportunities.filter(i=>i.processo===process).length!==1))return {status:STATUS.error,value:'Vínculo a validar'};
 const records=entries.map(([,r])=>r);
 if(field.id==='A0103')return {value:records.filter(r=>r.status==='AGUARDANDO_RETORNO').length};
 if(field.id==='A0105')return {value:records.filter(r=>r.next_follow_up_at?.slice(0,10)===todayYmd()).length};
 return {value:undefined};
}
function actualValue(field,context,item){
 if(['A0103','A0105'].includes(field.id))return statistic(field,context);
 const source=field.source;
 if(source.startsWith('monitor.opportunities.')){
  if(!item)return {status:STATUS.error,value:'Selecione um caso'};
  const path=source.slice('monitor.opportunities.'.length);
  const keys={id:'case_id',process_id:'processo',supplier_cnpj:'fornecedor_cnpj',route:'rota',contract_value:'valor_numero'};
  return {value:item[path.startsWith('payload_json.')?path.slice(13):keys[path]||path]};
 }
 if(/^monitor\.(outreach|outreach_history|proposals)/.test(source)){
  if(!item)return {value:undefined};
  const op=operationFor(context,item);
  if(['unavailable','ambiguous'].includes(op.status))return {status:STATUS.error,value:op.status==='ambiguous'?'Vínculo operacional a validar':'Indisponível'};
  if(source.startsWith('monitor.outreach.'))return {value:op.record?.[source.slice(17)]};
  if(source.startsWith('monitor.proposals.'))return {value:op.proposals.map(p=>p[source.slice(18)]).filter(present)};
  const prop=source.slice('monitor.outreach_history.'.length);
  return {value:(op.record?.history||[]).map(h=>h[prop]).filter(present)};
 }
 return {value:undefined};
}
export function resolveField(field,context,item){
 const base={id:field.id,status:field.status,value:field.empty,source:field.source,producer:field.producer};
 if(field.status===STATUS.demo)return {...base,hidden:true};
 if(field.status===STATUS.future)return base;
 if(field.status===STATUS.error)return {...base,value:'Indisponível'};
 if(!context?.feed)return {...base,status:STATUS.error,value:'Indisponível'};
 const result=actualValue(field,context,item);
 if(result.status===STATUS.error)return {...base,...result};
 if(!present(result.value))return {...base,status:STATUS.empty};
 let value=result.value;
 if(Array.isArray(value))value=value.map(v=>typeof v==='object'?JSON.stringify(v):v).join(' · ');
 else if(field.format==='Moeda BRL')value=brl(value);
 else if(typeof value==='boolean')value=value?'Sim':'Não';
 return {...base,status:STATUS.real,value:String(value)};
}
export function fieldSource(field,item){
 return `${field.source}${item?` · Caso ${item.case_id}`:''}. Produtor: ${field.producer}. Canal: ${field.channel}.`;
}
