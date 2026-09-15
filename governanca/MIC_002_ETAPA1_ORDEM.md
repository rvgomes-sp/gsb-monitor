[TRILHA: B.MENTOR → CURADOR]
[TIPO: ORDEM EXECUTIVA]
[ORDEM: MIC-002 — ETAPA 1]
[ASSUNTO: CONSTRUÇÃO ISOLADA DO MIC AUTÔNOMO]
[STATUS: AUTORIZADA — CÓDIGO + MIGRATION NÃO APLICADA + TESTES OFFLINE]

Curador,

por autorização expressa do Investidor, fica autorizada a construção
isolada do:

MIC — MOTOR DE IDENTIDADE DE CATÁLOGO

Esta ordem NÃO autoriza integração operacional.

O objetivo desta etapa é provar, exclusivamente por código e testes
offline, que o MIC pode existir como componente independente do Motor,
do Coletor, do B4 e do Monitor.

==================================================
1. ESTADO CANÔNICO DA FRENTE
==================================================

PROJETO SUPABASE CANÔNICO:

NOME:
gsb_monitor

PROJECT_REF:
wpsvmrmuxdvajjumdjqp

URL:
https://wpsvmrmuxdvajjumdjqp.supabase.co

REGIÃO:
sa-east-1

SCHEMA:
gsb

O estado remoto desse projeto decorre do checkpoint/inspeção canônica
já registrada.

IMPORTANTE:

Git comprova:
- arquivos;
- commits;
- migrations versionadas;
- conteúdo SQL.

Git NÃO será utilizado nesta entrega como prova autônoma de:
- migration aplicada remotamente;
- contagem de linhas;
- estado runtime do Supabase.

==================================================
2. ESTADO REMOTO A PRESERVAR
==================================================

Considerar como estado administrativo/técnico de referência:

MIGRATIONS APLICADAS:

20260911042757_evt007_factual_baseline_v1
20260911042811_evt007_catalog_bridge_v1

RELAÇÕES EXISTENTES:

gsb.evt007_collection_runs
gsb.evt007_raw_pages
gsb.evt007_results
gsb.evt007_item_identity
gsb.evt007_item_identity_observations
gsb.v_evt007_classified_results

ESTADO:

evt007_results = 0
evt007_item_identity = 0

EXECUÇÕES HISTÓRICAS:

evt007_20260909_stage2_v2_run1
evt007_20260909_stage2_v2_run2

Ambas:

source = COMPRASGOV_DADOS_ABERTOS
date = 2026-09-09
status = COMPLETE_EMPTY
results = 0
identities = 0

Esses registros são HISTÓRICOS.

PROIBIDO:

excluir;
corrigir;
reclassificar;
reexecutar;
substituir;
usar como run MIC.

==================================================
3. SEPARAÇÃO DE AMBIENTES
==================================================

Para esta ordem:

ÚNICO AMBIENTE FÍSICO DE REFERÊNCIA:

PROJECT_REF:
wpsvmrmuxdvajjumdjqp

SCHEMA:
gsb

Qualquer referência existente no repositório a:

licitacoes.*

é patrimônio documental/histórico de outra concepção.

NÃO assumir existência física dessas relações no projeto MIC.

NÃO usar licitacoes.* nesta implementação.

==================================================
4. COMPONENTES CONGELADOS
==================================================

Permanecem integralmente congelados:

Motor existente;
Coletor existente;
main;
Supabase anterior;
B4;
Monitor;
scheduler;
produção.

É PROIBIDO alterar qualquer arquivo em:

coletor/**
motor/**
monitor/**
monitor-vip/**

Incluindo expressamente:

coletor/run_coleta_evt007.py
coletor/pncp/motor.py
coletor/evt007_collect_pncp.py
coletor/evt007_collect_comprasgov.py
coletor/esteira_evt007.py
coletor/pncp/cliente.py
motor/evt007_rules_v3.py

==================================================
5. BRANCH
==================================================

Criar uma branch NOVA e isolada a partir da HEAD atual da main.

Nome recomendado:

feat/mic-002-autonomo-v01

Registrar no checkpoint:

MAIN_BASE_SHA
BRANCH_NAME
BRANCH_HEAD_SHA

A branch:

feat/evt007-catalog-bridge-v1

NÃO poderá ser mergeada ou cherry-picked integralmente.

Nenhum commit completo dessa branch será transplantado.

Ela poderá ser consultada somente como fonte histórica/técnica de:

funções;
contratos;
testes;
fixtures;
decisões de engenharia.

==================================================
6. RASTREABILIDADE DO REUSO
==================================================

Sempre que um conceito ou função for reimplementado com base no
experimento 003-S, registrar sua origem em:

governanca/MIC_ORIGENS_REUSO_v0.1.md

Para cada elemento reaproveitado registrar:

origem;
arquivo de origem;
commit/ref de origem;
conceito reaproveitado;
novo arquivo MIC;
adaptação realizada;
elementos expressamente descartados.

Reuso de conhecimento NÃO equivale à promoção da implementação antiga.

==================================================
7. PATHS AUTORIZADOS
==================================================

Somente poderão ser criados ou alterados:

mic/**

tests/test_mic_*

supabase/migrations/*mic*

governanca/*MIC*

Nenhum outro path está autorizado.

==================================================
8. ARQUITETURA DO MIC
==================================================

O componente deverá respeitar:

gsb.evt007_results
        ↓
      SELECT
        ↓
   MIC AUTÔNOMO
        ↓
ENRIQUECIMENTO OFICIAL ITEM-CÊNTRICO
        ↓
CATMAT / CATSER VERSIONADOS
        ↓
CAMADA MIC PRÓPRIA

FUTURAMENTE:

gsb.mic_runs
gsb.mic_identity_observations

Nesta etapa:

NENHUMA dessas tabelas existe remotamente por força desta ordem.

A migration será apenas escrita.

NÃO será aplicada.

==================================================
9. PROIBIÇÃO ABSOLUTA DE ESCRITA LEGADA
==================================================

O MIC NÃO poderá possuir caminho de escrita para:

gsb.evt007_results

gsb.evt007_collection_runs

gsb.evt007_raw_pages

gsb.evt007_item_identity

gsb.evt007_item_identity_observations

A view:

gsb.v_evt007_classified_results

é somente referência de compatibilidade.

Não haverá dupla escrita entre:

taxonomia experimental
e
taxonomia MIC.

==================================================
10. CONTRATO DE LEITURA FUTURO
==================================================

O repository do MIC poderá PREPARAR, mas não executar remotamente,
um contrato futuro de:

SELECT
FROM gsb.evt007_results

O código deve ser desenhado para receber os registros por injeção
ou repository abstraction.

Todos os testes desta etapa utilizarão fixtures offline.

Nenhuma conexão real ao PostgreSQL/Supabase será aberta.

==================================================
11. UNIVERSO DE ENTRADA
==================================================

O MIC não decide quem entra em evt007_results.

Para cada item recebido futuramente do universo factual autorizado:

case_id
+
item_number
+
source_name
+
resultado(s) associado(s)

o MIC poderá montar a chave item-cêntrica.

A seleção comercial é proibida.

Não aplicar:

valor mínimo;
tipo de obra;
regex;
biblioteca antiga;
porte;
natureza jurídica;
garantia;
score;
B4.

==================================================
12. DEDUPLICAÇÃO ITEM-CÊNTRICA
==================================================

Vários resultados poderão pertencer ao mesmo item.

A aquisição oficial de identidade deverá ocorrer:

UMA VEZ
POR:

case_id + item_number

dentro de um mesmo mic_run.

A função de chave deverá ser determinística.

Pode ser reimplementado o conceito histórico de:

item_key(["case_id", item_number])

desde que isolado no namespace MIC
e coberto por teste.

Não utilizar result_key como identidade do item.

==================================================
13. AQUISIÇÃO OFICIAL ITEM-CÊNTRICA
==================================================

Implementar o componente de aquisição.

NÃO EXECUTÁ-LO contra a internet nesta etapa.

A aquisição deverá ser encapsulada atrás de uma interface de transporte.

Produção futura:

MIC
→ item já conhecido
→ rota oficial autorizada
→ resposta oficial do item

O transport deverá permitir preservar:

URL exata;
HTTP status;
bytes exatos recebidos;
SHA-256 dos bytes;
payload parseado;
horário UTC de início;
horário UTC de término;
erro técnico, quando houver.

Nos testes:

usar transport falso/fixture.

PROIBIDO:

urllib real;
httpx real;
requests real;
socket real;
DNS real;
PNCP real;
Compras.gov real.

==================================================
14. API v1 E MANUAL 2.5
==================================================

Preservar o contrato arquitetural:

OpenAPI/API v1
= contrato das APIs Consulta e Integração

Manual PNCP 2.5
= documentação governante da estrutura,
campos, envelopes, limitações e interpretação.

Não são fontes concorrentes.

A implementação MIC não poderá criar nova interpretação incompatível
com os contratos já adotados pelo projeto.

==================================================
15. PROVENIÊNCIA DA IDENTIDADE
==================================================

A observação MIC deverá prever preservação de:

identity_source

identity_endpoint

identity_http_status

identity_payload_raw

identity_payload_sha256

identity_payload

identity_acquired_at

raw_field_presence

O SHA deverá ser calculado diretamente sobre:

identity_payload_raw

ANTES da interpretação JSON.

Teste obrigatório:

alterar 1 byte
→ SHA diferente.

==================================================
16. CAMPOS RAW
==================================================

Preservar separadamente quando presentes:

material_ou_servico_raw

catalogo_id_raw

catalogo_nome_raw

catalogo_codigo_item_raw

Nunca sobrescrever raw com valor normalizado.

Além do valor, preservar:

source_field_name
quando necessário para distinguir contratos de fonte.

Em especial:

catalogoCodigoItem

e:

codItemCatalogo

NÃO deverão ser tratados automaticamente como o mesmo campo bruto.

A implementação deverá permitir registrar qual nome de campo oficial
originou o valor.

==================================================
17. NAMESPACE
==================================================

Implementar roteamento literal:

"M"
→ CATMAT

"S"
→ CATSER

somente dentro do contrato de namespace explicitamente configurado
pelo MIC.

NÃO normalizar:

m
s
" S"
"S "
Material
Serviço
aliases
descrições.

Valor diferente de literal M/S:

NAMESPACE_NAO_COMPROVADO.

Esta implementação NÃO equivale, por si só, a ato formal de certificação
da regra de namespace.

==================================================
18. CATÁLOGOS
==================================================

O resolver deverá aceitar snapshots injetados.

Nesta etapa:

NÃO baixar CATMAT.

NÃO baixar CATSER.

NÃO consultar repositório externo.

Testes devem usar fixtures locais mínimas.

O contrato deverá prever:

catalog_snapshot_sha256
catalog_snapshot_scope
catalog_namespace
catalog_code

Lookup:

EXATAMENTE IGUALDADE DE CÓDIGO.

PROIBIDO:

contains;
prefixo;
regex;
fuzzy;
embedding;
descrição;
similaridade;
fallback entre CATMAT e CATSER.

==================================================
19. COLISÃO ENTRE NAMESPACES
==================================================

Teste obrigatório:

mesmo código
presente em fixture CATMAT
e
fixture CATSER

deve produzir:

duas identidades diferentes
dependentes exclusivamente do namespace.

Código isolado nunca define identidade.

==================================================
20. TAXONOMIA MIC CANÔNICA
==================================================

Utilizar exclusivamente no núcleo MIC:

MATCH_EXATO_CATMAT

MATCH_EXATO_CATSER

CODIGO_AUSENTE

NAMESPACE_NAO_COMPROVADO

CODIGO_OFICIAL_NAO_LOCALIZADO

IDENTIDADE_NAO_RESOLVIDA

ERRO_TECNICO

A taxonomia experimental:

CATSER_MATCH_EXATO
CATSER_NAO_LOCALIZADO
MATERIAL_PRESERVADO
CODIGO_CATALOGO_AUSENTE
NAMESPACE_NAO_RESOLVIDO
AQUISICAO_IDENTIDADE_FALHOU
ERRO_TECNICO_CATALOGO

NÃO será usada como taxonomia do MIC.

Não criar tradução com dupla persistência nesta etapa.

==================================================
21. reason_code
==================================================

Estados genéricos deverão carregar reason_code quando necessário.

Prever, no mínimo:

CONFLITO_IDENTIFICADORES

MULTIPLICIDADE_ITEM

EVIDENCIA_INSUFICIENTE

HASH_DIVERGENTE

SNAPSHOT_INDISPONIVEL

SNAPSHOT_HASH_DIVERGENTE

CHAVE_DUPLICADA_CATALOGO

CAMPO_RAW_INVALIDO

ESCOPO_NAMESPACE_NAO_COMPROVADO

ERRO_PARSE

ERRO_TRANSPORTE

Nenhum desses códigos representa decisão comercial.

==================================================
22. NULL
==================================================

Regra obrigatória:

código NULL/ausente
→ CODIGO_AUSENTE

Nunca:

NULL
→ CODIGO_OFICIAL_NAO_LOCALIZADO

Da mesma forma:

namespace não comprovado
→ NAMESPACE_NAO_COMPROVADO

Descrição nunca preenche NULL.

==================================================
23. NÃO LOCALIZADO
==================================================

CODIGO_OFICIAL_NAO_LOCALIZADO somente poderá ocorrer quando:

namespace comprovado para a execução;
código oficial presente;
snapshot carregado;
hash do snapshot validado;
lookup exato executado;
zero registros encontrados.

Registrar:

catalog_snapshot_scope = SNAPSHOT_ONLY

Esse estado NÃO significa:

"o código não existe no universo oficial".

==================================================
24. MULTIPLICIDADE
==================================================

Se a consulta de item retornar:

0 correspondências inequívocas;
ou
mais de 1 correspondência sem regra certificada de escolha;

não escolher arbitrariamente.

Resultado:

IDENTIDADE_NAO_RESOLVIDA

reason_code:
MULTIPLICIDADE_ITEM
ou
EVIDENCIA_INSUFICIENTE

conforme o caso.

==================================================
25. DIVERGÊNCIA DE IDENTIFICADORES
==================================================

Se:

case_id
item_number
idCompra
idCompraItem
ou outro identificador oficial esperado

divergirem entre input e resposta oficial:

falhar fechado.

Não corrigir por descrição.

Não escolher "o mais provável".

Resultado:

IDENTIDADE_NAO_RESOLVIDA

reason_code:
CONFLITO_IDENTIFICADORES

==================================================
26. MIGRATION A PREPARAR
==================================================

Criar UMA migration nova, não aplicada, contendo exclusivamente:

gsb.mic_runs

gsb.mic_identity_observations

PROIBIDO:

DROP
TRUNCATE
DELETE
ALTER de tabela evt007 existente
RENAME
VIEW nova
trigger
function
escrita de dados

==================================================
27. gsb.mic_runs — CONTRATO
==================================================

A migration deverá prever, no mínimo:

mic_run_id text PRIMARY KEY

mic_version text NOT NULL

status text NOT NULL

input_source text NOT NULL
DEFAULT 'gsb.evt007_results'

input_scope jsonb NOT NULL

namespace_rule_version text

catalog_refs jsonb

started_at timestamptz NOT NULL

finished_at timestamptz

metrics jsonb

error_message text

created_at timestamptz NOT NULL DEFAULT now()

Definir CHECK fechado para status apropriado à camada MIC.

Não utilizar estados de collection_run como sinônimos automáticos.

==================================================
28. gsb.mic_identity_observations — CONTRATO
==================================================

Prever, no mínimo:

mic_run_id
FK → gsb.mic_runs

item_key

case_id

item_number

source_result_keys jsonb

source_name

source_field_name

material_ou_servico_raw jsonb

catalogo_id_raw jsonb

catalogo_nome_raw jsonb

catalogo_codigo_item_raw jsonb

catalog_namespace text

catalog_code text

mic_status text

mic_reason_code text

resolution_method text

namespace_rule_version text

identity_source text

identity_endpoint text

identity_http_status integer

identity_payload_raw bytea

identity_payload_sha256 text

identity_payload jsonb

identity_started_at timestamptz

identity_acquired_at timestamptz

catalog_snapshot_sha256 text

catalog_snapshot_scope text

catalog_name text

catalog_group_code text

catalog_group_name text

failure_reason text

created_at timestamptz NOT NULL DEFAULT now()

PRIMARY KEY:

(mic_run_id, item_key)

Incluir constraints de integridade coerentes com a taxonomia MIC.

==================================================
29. RLS
==================================================

A migration preparada deverá:

ENABLE ROW LEVEL SECURITY

nas duas novas tabelas.

REVOKE ALL de:

PUBLIC
anon
authenticated

Nenhuma policy pública.

Se houver GRANT previsto para service_role:

limitar às novas tabelas MIC.

NÃO alterar grants ou policies de qualquer evt007_*.

==================================================
30. REPOSITORY MIC
==================================================

Implementar repository com dois contratos distintos.

READ SIDE:

futuramente:

SELECT
FROM gsb.evt007_results

WRITE SIDE:

futuramente exclusivamente:

INSERT gsb.mic_runs

INSERT gsb.mic_identity_observations

Não deverá existir SQL de escrita para:

evt007_results
evt007_collection_runs
evt007_raw_pages
evt007_item_identity
evt007_item_identity_observations

Teste deverá procurar explicitamente essas violações.

==================================================
31. NENHUMA EXECUÇÃO DE BANCO
==================================================

Nesta etapa:

não abrir DATABASE_URL;

não utilizar Supabase client;

não utilizar psycopg contra servidor real;

não executar migration;

não executar SELECT remoto;

não executar INSERT remoto.

Repository será testado com stub/fake/offline.

==================================================
32. ARQUIVOS RECOMENDADOS
==================================================

Estrutura mínima sugerida:

mic/__init__.py

mic/contracts.py
→ dataclasses/enums/taxonomia

mic/evidence.py
→ transporte abstrato
→ envelope de bytes/hash

mic/catalog.py
→ snapshots e lookup exato

mic/repository.py
→ contratos read/write SQL isolados

mic/engine.py
→ dedupe/item
→ namespace
→ resolução

mic/run.py
→ orquestração MIC sem side effect externo por padrão

tests/test_mic_contracts.py
tests/test_mic_evidence.py
tests/test_mic_catalog.py
tests/test_mic_engine.py
tests/test_mic_repository.py
tests/test_mic_architecture.py

supabase/migrations/<timestamp>_mic_autonomous_v01.sql

governanca/MIC_ORIGENS_REUSO_v0.1.md

Não é obrigatório usar exatamente essa divisão se houver solução menor,
mas qualquer variação deverá respeitar a allowlist de paths.

==================================================
33. TESTES OFFLINE OBRIGATÓRIOS
==================================================

Cobrir no mínimo:

T01
S + código CATSER fixture
→ MATCH_EXATO_CATSER

T02
M + código CATMAT fixture
→ MATCH_EXATO_CATMAT

T03
mesmo código CATMAT/CATSER
→ identidades diferentes

T04
código NULL
→ CODIGO_AUSENTE

T05
namespace NULL
→ NAMESPACE_NAO_COMPROVADO

T06
"s", " S", "S ", "Servico"
→ NAMESPACE_NAO_COMPROVADO

T07
código inexistente no snapshot
→ CODIGO_OFICIAL_NAO_LOCALIZADO
→ SNAPSHOT_ONLY

T08
descrição compatível + código NULL
→ continua CODIGO_AUSENTE

T09
hash de snapshot divergente
→ ERRO_TECNICO
→ zero lookup

T10
chave duplicada no catálogo fixture
→ ERRO_TECNICO

T11
identificadores divergentes
→ IDENTIDADE_NAO_RESOLVIDA

T12
multiplicidade de item
→ IDENTIDADE_NAO_RESOLVIDA

T13
dois resultados do mesmo item
→ uma aquisição

T14
bytes idênticos
→ SHA idêntico

T15
um byte alterado
→ SHA diferente

T16
rerun lógico com mesmo input/config
→ saída determinística

T17
nenhum código MIC importa:
coletor.*
motor.*
monitor.*

T18
nenhuma SQL de escrita aponta para:
evt007_results
evt007_collection_runs
evt007_raw_pages
evt007_item_identity
evt007_item_identity_observations

T19
migration contém somente:
mic_runs
mic_identity_observations
e seus índices/constraints/RLS/grants

T20
nenhum teste abre rede real

T21
nenhum teste abre banco remoto

==================================================
34. BLOQUEIO DE REDE NOS TESTES
==================================================

A suíte deve falhar se qualquer teste tentar rede real.

Usar transport injetável.

O módulo de aquisição poderá conter implementação futura da interface
oficial, mas ela não será chamada.

Testes de aquisição usam bytes de fixtures locais.

==================================================
35. FIXTURES
==================================================

Fixtures deverão ser:

sintéticas;
claramente identificadas como sintéticas;
pequenas;
determinísticas.

O Golden DNIT pode ser representado como fixture histórica de contrato
quando necessário, desde que fique explicitamente marcado:

FIXTURE / VETOR HISTÓRICO

e nunca como nova observação factual desta etapa.

==================================================
36. DIFERENÇA ENTRE IMPLEMENTADO, TESTADO E VALIDADO
==================================================

Ao final desta etapa será permitido declarar:

IMPLEMENTADO
se o código e a migration estiverem escritos.

TESTADO_OFFLINE
se a suíte aprovada passar.

NÃO será permitido declarar:

VALIDADO

CERTIFICADO

OPERACIONAL

INTEGRADO

PRODUTIVO

porque:

evt007_results = 0;
nenhuma API real será chamada;
nenhum Supabase será escrito;
nenhuma prova integrada será executada.

==================================================
37. DIFF CONTRA MAIN
==================================================

Ao concluir:

comparar integralmente:

main
vs
branch MIC

Entregar lista de todos os arquivos modificados.

Critério obrigatório:

100% dos arquivos modificados devem pertencer aos PATHS AUTORIZADOS.

Se qualquer path proibido aparecer:

PARAR.

NÃO corrigir silenciosamente a história.

Registrar ocorrência.

==================================================
38. HASHES
==================================================

Calcular SHA-256 dos principais artefatos:

migration MIC;

arquivos mic/*.py;

tests/test_mic_*.py;

MIC_ORIGENS_REUSO_v0.1.md;

relatório final.

Entregar manifesto:

governanca/MIC_002_ETAPA1_HASHES.sha256

==================================================
39. MIGRATION — PROVA DE NÃO APLICAÇÃO
==================================================

No relatório final declarar expressamente:

MIGRATION_CRIADA:
SIM/NÃO

MIGRATION_APLICADA:
NÃO

SUPABASE_ESCRITO:
NÃO

SUPABASE_CONSULTADO_RUNTIME:
NÃO

Nenhuma chamada apply_migration é autorizada.

==================================================
40. ROLLBACK
==================================================

Nesta etapa o rollback é trivial:

branch não mergeada;
migration não aplicada;
Supabase não escrito.

Se a implementação for rejeitada:

abandonar branch.

Não executar compensação no banco.

Não apagar histórico.

==================================================
41. CHECKPOINT OBRIGATÓRIO
==================================================

Responder exclusivamente ao B.Mentor:

[TRILHA: CURADOR → B.MENTOR]
[TIPO: ENTREGA — MIC-002 / ETAPA 1]

MAIN_BASE_SHA:
...

BRANCH:
...

BRANCH_HEAD_SHA:
...

PATHS_ALTERADOS:
...

PATHS_PROIBIDOS_ALTERADOS:
SIM/NÃO

ARQUITETURA_MIC:
...

DEPENDENCIA_MOTOR:
SIM/NÃO

DEPENDENCIA_COLETOR:
SIM/NÃO

DEPENDENCIA_MONITOR:
SIM/NÃO

MIGRATION:
...

TABELAS_PREVISTAS:
gsb.mic_runs
gsb.mic_identity_observations

MIGRATION_APLICADA:
NÃO

SUPABASE_ESCRITO:
NÃO

SUPABASE_RUNTIME_ACESSADO:
NÃO

REDE_EXTERNA_ACESSADA:
NÃO

TAXONOMIA_MIC:
...

LOOKUP_EXATO:
SIM/NÃO

FALLBACK_TEXTUAL:
SIM/NÃO

DEDUP_ITEM:
...

PRESERVACAO_BYTES:
...

SHA256:
...

TESTES:
...

TESTES_APROVADOS:
...

TESTES_FALHOS:
...

ORIGENS_REUSO:
...

DIFF_MAIN:
...

MANIFESTO_HASHES:
...

LIMITACOES:
- evt007_results permanece vazio;
- não houve integração real;
- não houve consulta real de identidade;
- não houve persistência real;
- não houve validação operacional.

ESTADO:
IMPLEMENTADO / NÃO IMPLEMENTADO

TESTADO_OFFLINE:
SIM/NÃO

VALIDADO:
NÃO

CERTIFICADO:
NÃO

ARTEFATOS:
...

OCORRENCIAS:
...

PARE.

==================================================
42. CONDIÇÃO DE PARADA
==================================================

Após:

código;
migration preparada;
testes offline;
diff;
hashes;
checkpoint;

PARE.

NÃO:

aplicar migration;
consultar Supabase;
consultar API;
popular banco;
executar ponte real;
alterar evt007.*;
tocar Motor;
tocar Coletor;
abrir B4;
tocar Monitor;
mergear main.

A próxima decisão pertence ao B.Mentor e ao Investidor.

==================================================
43. PRINCÍPIO DA ETAPA
==================================================

ESTA ETAPA NÃO PROVA QUE O MIC FUNCIONA EM PRODUÇÃO.

ESTA ETAPA PROVA APENAS QUE O MIC PODE SER CONSTRUÍDO:

FORA DO MOTOR;
FORA DO COLETOR;
FORA DO B4;
FORA DO MONITOR;

COM:

IDENTIDADE ITEM-CÊNTRICA;
EVIDÊNCIA PRESERVADA;
HASH REPRODUZÍVEL;
CATÁLOGO VERSIONADO;
LOOKUP EXATO;
TAXONOMIA PRÓPRIA;
FALHA FECHADA;
ZERO INFERÊNCIA COMO IDENTIDADE.

O FATO CONTINUA INTACTO.

O MIC SOMENTE ENRIQUECE.

B.MENTOR
VF_Intelligence_Plataform