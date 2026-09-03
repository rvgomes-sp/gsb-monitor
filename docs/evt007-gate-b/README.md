# Gate B — reconstrução governada do EVT-007

Entrega técnica para revisão do Mentor/Investidor. Nenhuma ativação operacional.
Branch: `feat/evt007-gate-b-governed`, derivada da `main`
`379aa408eb7e4e4b524b9ee25d254a3535a6a91a`.
PR visual #1 e branch visual não fazem parte desta alteração.

## Resultado

- Núcleo factual e inferencial isolado, com contrato versionado e sem escritor da carteira.
- **58 testes Python + 2 testes JavaScript aprovados**, exclusivamente offline.
- Replay de **16 páginas oficiais preservadas, 7.744 linhas, 6.976 fatos distintos**.
- Segunda execução não acrescenta fatos, revisões, decisões ou casos: apenas observações da nova execução.
- **42 oportunidades, 1 outreach, 1 histórico e 0 propostas preservados**, por contagem e SHA-256 antes/depois.
- Fonte viva e shadow do Gate C **não executados**. Nenhum scheduler, deploy de produção, migration ou merge.

O replay recebeu todas as páginas preservadas, mas detectou **768 linhas repetidas**.
Sua completude é `PARTIAL`, deliberadamente, não `COMPLETE`. Não se deduz ausência
de fatos apenas disso; cobertura única permanece incerta. Nenhum candidato pode
ser promovido a partir dessa coleta parcial.

Dos 6.976 fatos distintos, 6.966 não superam o piso. Os outros dez ficaram em
quarentena porque o arquivo de resultados não fornece modalidade; não se inventou
modalidade nem descrição. Há quatro resultados cancelados e quatro fornecedores
insuficientemente identificados, sobrepostos aos demais motivos, não somáveis
como grupos exclusivos. A classificação real desses dez não foi ensaiada com
enriquecimento ao vivo: isso pertence ao Gate C.

## Antes / depois

| Tema | Caminho legado observado | Novo núcleo isolado |
|---|---|---|
| Descoberta | caminhos concorrentes Compras.gov/PNCP | endpoint canônico Compras.gov fixo |
| Relógio | tratamento não uniformizado | consulta por `dataResultadoPncp`, relógio de resultado explicitamente mapeado; inclusão só latência |
| Piso | possibilidade de soma ou total de contratação | Decimal, resultado individual estritamente acima de R$10MM |
| Completude | interrupção por limite podia parecer conclusão | metadados/páginas/linhas verificados; `PARTIAL/FAILED` explícitos |
| Identidade | processo/dedup dependentes de caminho | processo + item + sequência factual; caso opaco persistente separado |
| Classificação | primeira regex de família vence; objeto geral antecipado | item → obrigação → papéis/limites → natureza → regra comercial |
| Catálogo | prefixo indevido de código para classe | prefixo removido; contrato presente, lookup não certificado bloqueado |
| Persistência | coletores/importadores podiam atingir estado operacional | SQLite de prova explícito, sem conexão ou escritor operacional |
| Import integral | exclusão e reconstrução de carteira | handler isolado retorna 410; sem banco/DDL/parsing do payload |

O contrato detalhado está em [CONTRATO.md](CONTRATO.md).

## Arquivos e funções

| Arquivo | Responsabilidade principal |
|---|---|
| `evt007/contracts.py` | `canonical`, `decode`, `money`, `integer`, `calendar_day`; contratos e hashes sem perda monetária |
| `evt007/collection.py` | `collect`, `fetch`, `public_get`; fonte, paginação, retry e preservação das respostas |
| `evt007/factual.py` | `normalize_result`, `process_reference`, `check_enrichment_origin`; grão, filtros, normalização e vínculo exato do item |
| `evt007/semantics.py` | `parse_obligation`, `decide`; representação intermediária, abstenção e regra GSB |
| `evt007/catalog.py` | `catalog_contract`, `retain_legacy_curation`; contrato sem simulação de certificação |
| `evt007/pipeline.py` | `evaluate`; elegibilidade antes da classificação, conflitos e deduplicação |
| `evt007/store.py` | `initialize`, `Store.record`, `Store.check_integrity`; transações, revisões e reserva de identidade isolada |
| `evt007/enrichment.py` | `enrich_known_results`; adaptador PNCP restrito, preparado para uso autorizado no Gate C |
| `evt007/__main__.py` | `init-ledger`, `replay`, `shadow`; comandos explícitos, sem agendamento |
| `tools/gate_b_replay_audit.py` | reprodução offline com hashes, duas execuções e `integrity_check` |
| `tests/evt007/` | regressões, segurança arquitetural e fixture oficial de três sequências |

Nenhum pacote adicional é necessário para o núcleo: biblioteca padrão Python
3.10+; versão efetivamente testada registrada no artefato de replay. Teste do
handler usa Node com `Request/Response` nativos. Não foi feito build completo do
Next nem novo aceite visual, pois UI/contrato visual não foram modificados.

## Legados retirados do caminho ativo nesta branch

`main()` bloqueado com erro explícito nos seguintes scripts:

- `coletor/run_coleta_evt007.py`
- `coletor/esteira_evt007.py`
- `coletor/ingest_consulta.py`
- `coletor/evt007_collect_comprasgov.py` — `run()` também bloqueado
- `coletor/evt007_collect_pncp.py`
- `motor/evt007_rules_v3.py` — `run()` também bloqueado
- `monitor/subir_ouro.py`
- `monitor/subir_obras.py`

`coletor/pncp/familias.py` passa a responder classificação pendente, sem inferência
de classe/grupo pelo prefixo nem promoção de obra. Os arquivos de catálogo não
foram alterados. Bibliotecas legadas restantes ficam apenas para rastreabilidade:
o novo pacote não as importa. Isso não é uma alegação de remoção universal de
toda função legada que alguém pudesse invocar manualmente.

`monitor-vip/app/api/import/snapshot/route.ts`: chamada sem token retorna 401;
chamada autenticada retorna 410 `IMPORT_SNAPSHOT_RETIRED`, sem acessar banco nem
ler corpo de importação. Os testes executam esse handler, não uma réplica.

**Importante:** esta neutralização está no código da branch técnica. Como não há
merge/deploy, a versão antiga em produção não foi substituída. Não executar a
rota antiga. Não se afirma que produção já recebeu essa proteção.

## Testes executados

```bash
python -B -m unittest discover -s tests/evt007 -p 'test_*.py' -v
node --test tests/evt007/import-route.test.mjs
git diff --check
```

Cobertura explícita:

- limite igual a R$10MM rejeitado, fração superior aceita, Decimal preservado;
- quinze itens de R$800 mil não viram um item de R$12 milhões;
- modalidades 1–19 confrontadas com conjunto permitido `{4,5,6,7}`;
- informado/cancelado/estado desconhecido, data inválida e inclusão sem poder de elegibilidade;
- identidade normalizada, item/sequência distintos, fornecedor alterado sem reassociação;
- três sequências reais no mesmo item/processo preservadas como três fatos;
- reexecução, reabertura da conexão, revisões, cancelamento e replay antigo sem reativação;
- falha transacional sem execução parcialmente gravada; falha de integridade bloqueia gravação;
- truncamento, metadados ausentes/contraditórios, página repetida, totais alterados, zero verdadeiro;
- 429, `Retry-After` em segundos/data, adiamento de espera longa, 401/403 sem contorno;
- orçamento do enriquecimento inclui retries e preserva evidência de 429;
- cinco contrastes semânticos obrigatórios, limites, contexto, acessórios e ambiguidade;
- catálogo não identificado por M/S, seis estados, curadoria histórica sem inferência de decisão humana;
- isolamento arquitetural e neutralização do import destrutivo.

Fixtures sintéticas são identificadas como testes e jamais enviadas a banco/API.
Esses testes não demonstram acurácia universal do parser nem cobertura nacional.

## Replay e integridade

Artefatos públicos, sem contatos/notas ou banco operacional:

- [source-manifest.json](source-manifest.json): hashes das 16 páginas consultadas;
- [replay-evidence.json](replay-evidence.json): resultados das duas execuções e SHA-256 do registro de prova;
- [integrity.json](integrity.json): contagens/hashes antes/depois do Supabase, comparação dos 42 hashes individuais e metadados;
- fixture oficial em `tests/evt007/fixtures/official_result_sequences.json`, com hash da página original.

O banco de prova completo e os payloads integrais não são publicados no Git:
podem conter dados de pessoas físicas presentes na fonte. O manifesto permite
reproduzir o replay sobre o acervo custodiado, sem nova coleta.

Incidente de ambiente: a repetição com SQLite dentro da árvore gerenciada de
trabalho produziu `database disk image is malformed`. Foi reproduzida e não
ocultada. A repetição em diretório temporário isolado **fora dessa árvore** passou
duas vezes, incluindo a versão final, com `integrity_check=ok`. A causa sistêmica
exata não foi estabelecida; a inspeção de syscalls foi negada e não houve contorno.
Fechamento explícito da conexão de inicialização e checagens antes da transação
foram adicionados. Não reutilizar os arquivos danificados nem certificar esse
local de armazenamento para shadow. Não há evidência de corrupção no Supabase.

O Gate C precisa utilizar armazenamento isolado validado. O resultado desta prova
não autoriza persistência de produção em `/tmp` ou neste SQLite.

## Migrations

**Nenhuma migration Supabase/produção.** O único schema novo é o registro SQLite
de prova, inicializado por comando explícito e nunca em request/runtime. O
contrato não foi aplicado ao banco operacional.

## Pendências e próximo gate — não executado

1. Aprovação desta implementação e do tratamento conservador de completude.
2. Shadow controlado em ambiente isolado validado, com data, páginas e orçamento HTTP aprovados.
3. Medir qualidade/cobertura do parser com descrições reais de itens elegíveis; limites gramaticais não são preenchidos por suposição.
4. Resolver vínculo dos eventos novos com os 42 casos sem chave por processo isolado, sem recriar a memória comercial.
5. Congelar regras comerciais das naturezas além de obra antes de promovê-las.
6. Certificar equivalência PNCP–catálogo antes de liberar `CODIGO_OFICIAL`; revalidar custódia CATMAT separadamente.
7. Validar tratamento de revisões históricas com autoridade da fonte, não ordem de chegada.

O comando `shadow` exige `--acknowledge-gate-c-authorization`. Esse parâmetro é uma
trava de uso acidental, não substitui autorização do Mentor/Investidor. O adaptador
PNCP é opt-in com `--enrich-pncp --enrichment-request-budget N`; não transforma
PNCP em descoberta. Nenhum comando escreve no Monitor, mesmo no modo shadow.

**Parada desta entrega:** nenhum merge, produção, motor vivo, OSINT ou edital.
