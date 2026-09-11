[TRILHA: B.MENTOR → CURADOR]
[TIPO: ORDEM EXECUTIVA DEFINITIVA]
[ORDEM: 003-S — CONTROLE 02-R / ETAPA 3]
[ASSUNTO: TESTE CANÔNICO EVT-007 — MOTOR DE FRESCOR + PONTE OFICIAL DE CATÁLOGO + SUPABASE]
[STATUS: AUTORIZADA]
[SUBSTITUI: TODAS AS ORDENS ANTERIORES CONFLITANTES DA ETAPA 3]

Curador,

após revisão conjunta entre Investidor e B.Mentor, fica definida a
arquitetura definitiva desta prova.

O projeto NÃO está construindo um novo EVT-007.

O motor de descoberta existe.

O drill de itens existe.

O drill de resultados existe.

A lógica de frescor existe.

O trabalho desta etapa é:

RETIRAR A INFERÊNCIA COMO PORTEIRO
+
FAZER O RESULTADO HOMOLOGADO REAL ATRAVESSAR
A PONTE OFICIAL DE CATÁLOGO
+
PERSISTIR FATO E IDENTIDADE NO SUPABASE.

==================================================
1. COMPONENTES CANÔNICOS
==================================================

REPOSITÓRIO:

rvgomes-sp/gsb-monitor

BRANCH:

feat/evt007-catalog-bridge-v1

ENTRADA OPERACIONAL:

coletor/run_coleta_evt007.py

MOTOR:

coletor/pncp/motor.py

CLIENTE PNCP:

coletor/pncp/cliente.py

FRESCOR:

coletor/pncp/frescor.py

SUPABASE FACTUAL:

PROJECT_REF:
wpsvmrmuxdvajjumdjqp

==================================================
2. FLUXO CANÔNICO DESTA PROVA
==================================================

O fluxo obrigatório é:

MODALIDADES 4–7
↓
/contratacoes/atualizacao
↓
contratações acima do piso vigente do motor
↓
/itens
↓
TODOS os itens com temResultado=true
↓
/itens/{n}/resultados
↓
dataResultado × dataInclusao
↓
evento EVT-007 do dia
↓
FRESH / EXCEPTION / BACKFILL
↓
itens únicos envolvidos nesses eventos
↓
materialOuServico + codItemCatalogo
↓
CERT-NS-001
↓
S → CATSER
M → CATMAT preservado
↓
SUPABASE factual
↓
rerun
↓
auditoria
↓
PARE

A ponte ocorre DEPOIS da identificação dos resultados/eventos do dia.

Não consultar catálogo para itens que não participaram do evento
que está sendo processado.

==================================================
3. MODALIDADES
==================================================

Preservar exatamente:

MODALIDADES_PADRAO = [4, 5, 6, 7]

Não ampliar.

Não reduzir.

==================================================
4. DESCOBERTA DIÁRIA
==================================================

Preservar a descoberta existente:

Consulta PNCP
/v1/contratacoes/atualizacao

com:

dataInicial = DATA_ALVO
dataFinal = DATA_ALVO
codigoModalidadeContratacao = 4,5,6,7

Preservar:

paginação;
retry;
tratamento de erro;
pacing;
max_pages=0 para leitura completa.

Não utilizar:

coletor/evt007_collect_comprasgov.py

como entrada produtiva desta prova.

Esse componente permanece preservado como ferramenta
auxiliar/diagnóstica.

==================================================
5. INSTRUMENTAÇÃO DA DESCOBERTA
==================================================

O motor deverá distinguir obrigatoriamente:

A.
quantas contratações a fonte devolveu;

B.
quantas passaram pelo piso econômico.

Registrar por modalidade e consolidado:

PAGINAS_LIDAS

PAGINAS_PULADAS

CONTRATACOES_ATUALIZADAS_LIDAS

CONTRATACOES_ACIMA_PISO

Nunca interpretar:

CONTRATACOES_ACIMA_PISO = 0

como:

"não houve licitações".

==================================================
6. PISO ECONÔMICO
==================================================

Nesta ordem NÃO redesenhar a regra econômica.

Preservar o comportamento vigente do motor:

valorTotalHomologado >= R$ 10.000.000

na fase de descoberta da contratação.

Registrar explicitamente que esse piso pertence ao motor vigente
e está sendo preservado apenas para esta prova.

Não criar nesta etapa nova regra de agregação econômica.

==================================================
7. AQUISIÇÃO DE ITENS
==================================================

Para cada contratação descoberta:

executar:

GET /itens

Preservar integralmente os itens retornados.

Registrar:

TOTAL_ITENS_LIDOS

TOTAL_ITENS_COM_RESULTADO

==================================================
8. REMOÇÃO DEFINITIVA DO PORTÃO INFERENCIAL
==================================================

Hoje o motor utiliza:

clf.classificar_contratacao(...)

e permite que:

NAO_OBRA

interrompa a execução.

Também utiliza:

cl.itens_obra

para escolher quais itens seguem ao drill.

ESSAS DUAS FUNÇÕES DECISÓRIAS DEIXAM DE EXISTIR
NO CAMINHO CANÔNICO.

A inferência não poderá:

eliminar contratação;
eliminar item;
selecionar item;
bloquear /resultados;
definir namespace;
definir catálogo;
definir aderência.

O classificador legado pode permanecer somente como:

DIAGNÓSTICO PARALELO

desde que sua saída não altere o fluxo.

==================================================
9. ALVO DO DRILL
==================================================

O conjunto de itens que segue para /resultados será:

TODOS OS ITENS COM:

temResultado = true

e não:

cl.itens_obra

Não aplicar qualquer filtro textual antes do drill.

==================================================
10. RESULTADOS
==================================================

Executar:

GET /itens/{numeroItem}/resultados

para todos os itens elegíveis do item 9.

Preservar, quando presentes:

sequencialResultado
niFornecedor
nomeRazaoSocialFornecedor
porteFornecedor
naturezaJuridica
quantidadeHomologada
valorUnitarioHomologado
valorTotalHomologado
dataResultado
dataInclusao
dataAtualizacao
dataCancelamento
motivoCancelamento
payload oficial

Registrar:

TOTAL_RESULTADOS_LIDOS

TOTAL_RESULTADOS_POR_ITEM

==================================================
11. FRESCOR
==================================================

Preservar a lógica existente:

fr.avaliar(
    dataResultado,
    dataInclusao
)

Preservar a identificação do evento da DATA_ALVO por:

dataInclusao.date() == DATA_ALVO

Preservar as classificações vigentes do módulo:

FRESH
EXCEPTION
BACKFILL

Não alterar seus critérios nesta ordem.

Registrar:

TOTAL_EVENTOS_INCLUIDOS_NO_DIA

N_FRESH

N_EXCEPTION

N_BACKFILL

O frescor responde:

"QUAL RESULTADO ENTROU AGORA?"

==================================================
12. FATO ANTES DO ENRIQUECIMENTO
==================================================

REGRA ESTRUTURAL:

UM RESULTADO FACTUAL COMPROVADO NÃO PODE DESAPARECER
POR FALHA POSTERIOR DA PONTE.

Portanto:

resultado/frescor factual
e
identidade catalográfica

são camadas independentes.

Se ocorrer:

falha de aquisição da identidade;
NULL de namespace;
ausência de código;
erro CATSER;
não localização no catálogo;

o resultado factual permanece preservado.

==================================================
13. CONJUNTO QUE ENTRA NA PONTE
==================================================

Depois do drill e da avaliação de frescor:

identificar os ITENS ÚNICOS envolvidos nos eventos da DATA_ALVO.

Chave conceitual:

contratação + numeroItem

Um mesmo item com múltiplos resultados não autoriza múltiplas
aquisições idênticas de identidade.

Registrar:

TOTAL_ITENS_UNICOS_COM_EVENTO

==================================================
14. AQUISIÇÃO DA IDENTIDADE OFICIAL
==================================================

Para cada item único do item 13:

preservar/obter:

materialOuServico
codItemCatalogo

Se materialOuServico já estiver disponível na resposta oficial de
/itens:

preservar exatamente o valor bruto.

Se codItemCatalogo não estiver disponível nessa resposta:

utilizar exclusivamente a rota oficial já certificada no Controle 02:

Dados Abertos Compras.gov
2.1_consultarItensContratacoes_PNCP_14133_Id

Essa chamada NÃO é mecanismo de descoberta.

Ela serve exclusivamente para completar a identidade oficial
de um item já descoberto pelo motor EVT-007.

==================================================
15. IDENTIFICADORES
==================================================

Preservar sempre que disponíveis:

numeroControlePNCP
idContratacaoPNCP
numeroItem
numeroItemPncp
idCompra
idCompraItem

Não fabricar identificadores.

Não reconciliar divergências por descrição.

Identificadores conflitantes:

AQUISICAO_IDENTIDADE_FALHOU

com evidência preservada.

==================================================
16. DEDUPLICAÇÃO DA PONTE
==================================================

Uma consulta de identidade por ITEM ÚNICO.

Registrar:

CHAMADAS_IDENTIDADE_REALIZADAS

O valor esperado deverá ser compatível com:

TOTAL_ITENS_UNICOS_COM_EVENTO

salvo casos em que a própria resposta de /itens já contenha
toda a identidade necessária e nenhuma chamada adicional seja requerida.

Explicar qualquer diferença.

==================================================
17. NAMESPACE — CERT-NS-001
==================================================

Aplicar exclusivamente:

materialOuServico exatamente "S"
→ catalog_namespace = CATSER

materialOuServico exatamente "M"
→ catalog_namespace = CATMAT

outro / NULL
→ NAMESPACE_NAO_RESOLVIDO

Não normalizar.

Não mapear aliases.

Não utilizar descrição.

==================================================
18. CATSER
==================================================

Para:

materialOuServico = "S"

e:

codItemCatalogo presente

utilizar exclusivamente o snapshot CATSER certificado:

SHA-256:

f3cd884220115be97fd7782a25e799d8c64390786794d27c3fef53806e67f264

Recalcular o hash antes do lookup.

Se divergir:

ERRO_TECNICO_CATALOGO

e interromper o lookup nesse arquivo.

MATCH permitido exclusivamente:

codigoServico == codItemCatalogo

Estados:

CATSER_MATCH_EXATO

CATSER_NAO_LOCALIZADO

CODIGO_CATALOGO_AUSENTE

ERRO_TECNICO_CATALOGO

==================================================
19. CATMAT
==================================================

Para:

materialOuServico = "M"

preservar:

materialOuServico_raw

codItemCatalogo_raw

catalog_namespace = CATMAT

catalog_code, quando canônico

catalog_match_status = MATERIAL_PRESERVADO

Não executar lookup CATMAT nesta ordem.

==================================================
20. NULL E FALHAS
==================================================

Preservar estados reais:

NAMESPACE_NAO_RESOLVIDO

CODIGO_CATALOGO_AUSENTE

AQUISICAO_IDENTIDADE_FALHOU

ERRO_TECNICO_CATALOGO

NULL nunca autoriza inferência.

Descrição nunca substitui identificador oficial.

==================================================
21. SUPABASE
==================================================

Destino:

wpsvmrmuxdvajjumdjqp

Utilizar as relações já criadas:

gsb.evt007_collection_runs

gsb.evt007_raw_pages

gsb.evt007_results

gsb.evt007_item_identity

gsb.evt007_item_identity_observations

gsb.v_evt007_classified_results

Não criar banco paralelo.

Não utilizar outro Supabase.

==================================================
22. PERSISTÊNCIA DO FATO
==================================================

Persistir o fato EVT-007 independentemente do sucesso da ponte.

Preservar:

contratação
item
sequencialResultado
fornecedor
valor
quantidade
dataResultado
dataInclusao
datas auxiliares
payload oficial
fonte

A identidade catalográfica é enriquecimento ligado ao item.

Não é condição de existência do fato.

==================================================
23. PERSISTÊNCIA DO FRESCOR
==================================================

Verificar se o contrato físico atual permite auditar:

dataResultado

dataInclusao

delta_calendar_days

delta_business_days

freshness_class

Se os campos derivados de frescor ainda não puderem ser preservados
sem perda:

propor e aplicar somente migration ADITIVA mínima e versionada.

Nenhum DROP.

Nenhum TRUNCATE.

Nenhuma reescrita histórica.

Os campos brutos de dataResultado e dataInclusao permanecem
sempre obrigatórios.

==================================================
24. DATA CONTROLADA DA PROVA
==================================================

DATA_ALVO:

2026-09-10

Executar explicitamente essa data.

Não usar escolha automática.

MODALIDADES:

4,5,6,7

MAX_PAGES:

0

==================================================
25. PRIMEIRO RUN — DRY-RUN
==================================================

Primeiro executar SEM escrita.

Relatar obrigatoriamente:

PAGINAS_LIDAS

PAGINAS_PULADAS

CONTRATACOES_ATUALIZADAS_LIDAS

CONTRATACOES_ACIMA_PISO

TOTAL_ITENS_LIDOS

TOTAL_ITENS_COM_RESULTADO

TOTAL_RESULTADOS_LIDOS

TOTAL_EVENTOS_INCLUIDOS_NO_DIA

N_FRESH

N_EXCEPTION

N_BACKFILL

TOTAL_ITENS_UNICOS_COM_EVENTO

N_S

N_M

N_NAMESPACE_NAO_RESOLVIDO

N_S_COM_CODIGO

N_S_SEM_CODIGO

N_CATSER_MATCH_EXATO

N_CATSER_NAO_LOCALIZADO

N_MATERIAL_PRESERVADO

N_AQUISICAO_IDENTIDADE_FALHOU

N_ERRO_TECNICO_CATALOGO

CHAMADAS_IDENTIDADE_REALIZADAS

==================================================
26. INTERPRETAÇÃO DE ZERO
==================================================

Se:

CONTRATACOES_ATUALIZADAS_LIDAS = 0

nas quatro modalidades,
com paginação integral e respostas tecnicamente válidas:

NÃO concluir:

"NÃO HOUVE LICITAÇÃO".

Registrar:

RESULTADO ANÔMALO DA CONSULTA DE DESCOBERTA

preservar evidência e PARE.

Se:

CONTRATACOES_ATUALIZADAS_LIDAS > 0

e:

CONTRATACOES_ACIMA_PISO = 0

registrar:

HOUVE ATIVIDADE NA FONTE;
NENHUMA CONTRATAÇÃO PASSOU PELO PISO DO MOTOR.

Se:

CONTRATACOES_ACIMA_PISO > 0

mas:

TOTAL_EVENTOS_INCLUIDOS_NO_DIA = 0

registrar:

HOUVE DESCOBERTA ACIMA DO PISO;
NENHUM RESULTADO FOI INCLUÍDO NA DATA_ALVO SEGUNDO A REGRA DE FRESCOR.

Não misturar os estágios.

==================================================
27. CONDIÇÃO PARA PRIMEIRA PERSISTÊNCIA
==================================================

Persistir somente se o dry-run demonstrar:

A.
descoberta funcional;

B.
paginação funcional;

C.
/itens funcional;

D.
/resultados funcional;

E.
frescor funcional;

F.
inferência sem poder de bloqueio;

G.
ponte executando sobre itens reais;

H.
nenhuma inconsistência estrutural que comprometa a evidência.

==================================================
28. PRIMEIRO RUN PERSISTIDO
==================================================

Executar novamente:

DATA_ALVO = 2026-09-10

com run_id próprio.

Registrar contagens ANTES e DEPOIS de:

evt007_collection_runs

evt007_raw_pages

evt007_results

evt007_item_identity

evt007_item_identity_observations

==================================================
29. RERUN
==================================================

Executar novamente a MESMA DATA_ALVO com outro run_id.

Objetivo:

provar idempotência real no PostgreSQL.

Esperado:

collection_runs
→ cresce por execução

raw_pages
→ cresce por aquisição

item_identity_observations
→ cresce por run/item

evt007_results
→ NÃO duplica o mesmo result_key

evt007_item_identity
→ NÃO duplica o mesmo item_key

Nova execução não equivale a novo fato.

==================================================
30. DIVERGÊNCIA ENTRE EXECUÇÕES
==================================================

Se o mesmo item retornar identidade oficial diferente no rerun:

não sobrescrever silenciosamente.

Preservar a nova observação.

Registrar:

OCC-EVT007-IDENTITY-DRIFT-001

Não criar nova política temporal nesta ordem.

==================================================
31. TESTE OBRIGATÓRIO DA REMOÇÃO DA INFERÊNCIA
==================================================

Produzir prova específica de que:

um item classificado pelo legado como:

NAO_OBRA

NÃO é bloqueado.

Ele deve poder:

chegar a /resultados;

ser avaliado pelo frescor;

participar do evento factual, se aplicável;

receber tentativa de identidade oficial;

ser persistido factualmente.

Isso certifica que a inferência deixou de ser porteiro.

==================================================
32. AUDITORIA ITEM A ITEM
==================================================

Para cada resultado/evento da prova entregar:

case_id

item_number

result_sequence

supplier_identifier

supplier_name

homologated_total_value

dataResultado

dataInclusao

delta_calendar_days

delta_business_days

freshness_class

materialOuServico_raw

codItemCatalogo_raw

catalog_namespace

catalog_code

catalog_name

catalog_group_code

catalog_group_name

catalog_match_status

identity_endpoint

identity_payload_hash

failure_reason

==================================================
33. CRITÉRIO DE SUCESSO DA PONTE
==================================================

A ponte estará OPERACIONALMENTE PROVADA quanto à identidade se houver
ao menos um item real com:

EVT-007 factual
↓
item oficial
↓
materialOuServico adquirido
↓
namespace determinado

Para provar CATSER em operação será necessário adicionalmente:

materialOuServico = "S"
+
codItemCatalogo
+
resultado do lookup exato.

Se a safra real contiver somente materiais:

declarar:

PONTE DE IDENTIDADE = EXERCIDA

PONTE CATSER = NÃO EXERCIDA POR AUSÊNCIA DE CASO S

Não fabricar caso de teste real.

==================================================
34. MONITOR — NÃO ESCREVER NESTA ORDEM
==================================================

O objetivo final do projeto permanece:

SUPABASE
→ MONITOR

Porém NÃO executar escrita no Monitor nesta etapa.

É proibido utilizar:

monitor-vip/app/api/import/snapshot/route.ts

porque o mecanismo histórico executa substituições destrutivas.

Não executar:

DELETE monitor.opportunities

DELETE monitor.proposals

DELETE monitor.outreach_history

TRUNCATE

substituição integral de feed

recriação dos IDs existentes.

==================================================
35. ESPECIFICAÇÃO DA FUTURA PROMOÇÃO
==================================================

Como parte da entrega, produzir somente a ESPECIFICAÇÃO da futura
promoção aditiva:

Supabase
→ Monitor

Ela deverá definir:

identidade da oportunidade;

process_id;

supplier_cnpj;

valor;

evento/frescor;

identidade catalográfica;

payload;

regra de idempotência;

regra para caso já existente;

regra para caso novo;

preservação de outreach;

preservação de histórico;

preservação de propostas.

NÃO implementar nem executar ainda.

==================================================
36. OBJETOS FORA DO ESCOPO
==================================================

Não abrir nesta ordem:

B4

Motor de Edital

OSINT

lookup CATMAT

redesenho do Monitor

redesenho de identidade comercial definitiva

merge em main

deploy de produção

==================================================
37. MAIN
==================================================

main permanece intocada.

Todo trabalho continua isolado na branch autorizada.

Não mergear.

==================================================
38. ENTREGA FINAL
==================================================

Responder exclusivamente:

[TRILHA: CURADOR → B.MENTOR]
[TIPO: ENTREGA — 003-S / CONTROLE 02-R / ETAPA 3]

REPOSITÓRIO:
rvgomes-sp/gsb-monitor

BRANCH:
feat/evt007-catalog-bridge-v1

COMMIT:
...

DATA_ALVO:
2026-09-10

MODALIDADES:
4,5,6,7

ENTRADA:
coletor/run_coleta_evt007.py

MOTOR:
coletor/pncp/motor.py

INFERENCIA_COMO_PORTEIRO:
REMOVIDA / NÃO REMOVIDA

PAGINAS_LIDAS:
...

PAGINAS_PULADAS:
...

CONTRATACOES_ATUALIZADAS_LIDAS:
...

CONTRATACOES_ACIMA_PISO:
...

TOTAL_ITENS_LIDOS:
...

TOTAL_ITENS_COM_RESULTADO:
...

TOTAL_RESULTADOS_LIDOS:
...

TOTAL_EVENTOS_INCLUIDOS_NO_DIA:
...

N_FRESH:
...

N_EXCEPTION:
...

N_BACKFILL:
...

TOTAL_ITENS_UNICOS_COM_EVENTO:
...

N_S:
...

N_M:
...

N_NAMESPACE_NAO_RESOLVIDO:
...

N_S_COM_CODIGO:
...

N_S_SEM_CODIGO:
...

N_CATSER_MATCH_EXATO:
...

N_CATSER_NAO_LOCALIZADO:
...

N_MATERIAL_PRESERVADO:
...

N_AQUISICAO_IDENTIDADE_FALHOU:
...

N_ERRO_TECNICO_CATALOGO:
...

CHAMADAS_IDENTIDADE_REALIZADAS:
...

CATSER_SHA256:
...

SUPABASE:
wpsvmrmuxdvajjumdjqp

RUN1:
...

RERUN:
...

CONTAGENS_ANTES:
...

CONTAGENS_DEPOIS_RUN1:
...

CONTAGENS_DEPOIS_RERUN:
...

IDEMPOTENCIA:
...

TESTE_NAO_OBRA_SEM_BLOQUEIO:
...

AUDITORIA:
...

VIEW_CLASSIFICADA:
...

ESPECIFICACAO_PROMOCAO_MONITOR:
...

O_QUE_FOI_PROVADO:
...

O_QUE_NAO_FOI_PROVADO:
...

OCORRENCIAS:
...

ARTEFATOS_DRIVE:
...

PARE.

Nenhuma ação posterior está autorizada.

A próxima decisão pertence ao B.Mentor.

==================================================
39. PRINCÍPIO FINAL
==================================================

O MOTOR JÁ SABE ONDE PROCURAR.

O DRILL JÁ SABE ENCONTRAR OS RESULTADOS.

O FRESCOR JÁ SABE QUAL EVENTO ENTROU AGORA.

A PONTE PASSA A DIZER, OFICIALMENTE, O QUE É O ITEM.

PORTANTO:

DESCOBERTA
→ ITEM
→ RESULTADO
→ FRESCOR
→ IDENTIDADE OFICIAL
→ CATÁLOGO
→ SUPABASE.

A INFERÊNCIA NÃO DECIDE MAIS QUEM PASSA.

O FATO EXISTE ANTES DO ENRIQUECIMENTO.

A FALHA DO CATÁLOGO NÃO APAGA O FATO.

O MONITOR SÓ SERÁ ALIMENTADO APÓS CERTIFICAÇÃO DESTA CADEIA.

B.MENTOR
VF_Intelligence_Plataform