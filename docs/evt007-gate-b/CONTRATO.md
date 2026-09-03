# EVT-007 — contrato implementado no Gate B

Status: implementação isolada; nenhuma autorização de promoção operacional.
Versões: `evt007-gate-b-1`, `obligation-grammar-1`, `gsb-domain-obra-1`.

## Fonte, relógios e filtro

Descoberta exclusivamente em Dados Abertos Compras.gov:
`/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133`.
Consulta com `dataResultadoPncpInicial/Final`, página e tamanho explícitos.
PNCP não é fonte alternativa de descoberta.

No DTO e no acervo preservado o nome do campo do resultado é
`dataResultadoPncp`. A normalização expõe esse relógio de negócio como
`dataResultado`, registrando `dataResultado_source_field=dataResultadoPncp`.
Não existe um segundo `dataResultado` independente nos exemplos preservados.
Um payload que forneça os dois com datas diferentes fica em quarentena, até
validação do mapeamento; não se escolhe silenciosamente um deles.
`dataInclusaoPncp` permanece bruto e serve apenas à latência em dias-calendário.

Fontes de referência: [OpenAPI oficial](https://dadosabertos.compras.gov.br/v3/api-docs)
e [Manual de Dados Abertos Compras.gov](https://www.gov.br/compras/pt-br/acesso-a-informacao/manuais/manual-dados-abertos/manual-api-compras.pdf/@@download/file),
seção de resultados PNCP, páginas 103–106. Consulta documental não equivale a
shadow run de resultados.

Elegibilidade factual requer cumulativamente:

- resultado informado (`situacaoCompraItemResultadoId=1`), data válida e ausência de cancelamento;
- modalidade confirmada em `{4,5,6,7}`;
- `valorTotalHomologado` individual, com `Decimal`, estritamente maior que `10000000`;
- identidade e fornecedor suficientes, sem contradição com o enriquecimento.

Não há soma, multiplicação de unitário por quantidade ou substituição pelo total
da contratação. Ausências/contradições não viram zero. Resultado cancelado,
modalidade fora do conjunto e valor não superior ao piso são inelegíveis.
Demais insuficiências são explícitas: `QUARENTENA` e códigos de motivo.

## Identidades distintas

| Identidade | Definição | O que não significa |
|---|---|---|
| `process_id` | referência PNCP normalizada: órgão, sequência da contratação, ano | identidade única do caso |
| resultado factual | namespace da fonte + `process_id` + `numero_item` + `sequencial_resultado` | agregado do processo ou de fornecedores |
| `event_id` | `evt007:` + SHA-256 da identidade normalizada | hash do payload mutável |
| revisão | `event_id` + hash da representação JSON do resultado bruto | evento novo por mudança de valor/data |
| observação | execução + evento + revisão | duplicação de fato |
| `case_id` | UUID opaco persistido, reservado apenas no registro isolado | chave derivada de `process_id` ou vínculo criado na carteira |

Fornecedor, valor e datas não entram na identidade do resultado: revisões devem
continuar rastreáveis. Troca de fornecedor bloqueia reassociação automática do
caso. Múltiplas revisões exigem validação; ordem de chegada não é autoridade para
reativar um candidato cancelado. Não há chave substituta para identidade ausente.

Prova de grão: a fixture oficial contém três resultados do mesmo item/processo,
com sequências distintas. O manifesto da fixture identifica página e hash de
origem. Isto prova que processo/item sozinho é insuficiente. Não prova vínculo
automático entre o novo namespace e os 42 casos legados. Esse vínculo permanece
pendente de resolução governada, sem reconstruir ou renumerar a carteira.

## Coleta e completude

`COMPLETE` exige todas as páginas esperadas, metadados consistentes, número de
linhas compatível e ausência de anomalias. `max_pages` nunca certifica truncamento.
`PARTIAL` preserva o recebido, mas bloqueia candidatos. `FAILED` indica que não
foi possível obter linhas válidas. Uma resposta HTTP 200 malformada é preservada.

Política conservadora desta implementação: repetição exata de linhas na
paginação gera `PARTIAL`, mesmo com quantidade bruta igual ao total informado.
Isso sinaliza dúvida sobre cobertura de registros únicos, não afirma que haja
registros faltantes. Os fatos repetidos são deduplicados separadamente.

HTTP 429/5xx transitórios: até quatro tentativas, backoff e respeito a
`Retry-After`. Espera superior ao teto local de 60 segundos retorna adiamento;
não há retry antecipado, troca de IP, credencial ou endpoint. 401/403 encerram a
tentativa sem contorno. Tentativas, respostas, hashes e falhas permanecem visíveis.

PNCP pode enriquecer somente processos/itens conhecidos, já descobertos na fonte
canônica. O adaptador preparado usa duas rotas exatas: contratação conhecida
(modalidade/contexto) e item conhecido (descrição). Possui orçamento explícito de
requisições, incluindo retries, cache por chave e parada em restrição de acesso.
Não há busca nacional, árvore de catálogo, edital ou OSINT nesse adaptador.

## Representação intermediária e decisão

Campos preservados pelo parser:

```text
descricao_item_raw / objeto_contexto_raw
obrigacao_principal / natureza_contratual
meios_execucao[] / insumos[] / obrigacoes_acessorias[]
negativas[] / limitacoes[] / destinacao[]
trecho_suporte_obrigacao / trecho_suporte_natureza
suporte_spans[] { inicio, fim, texto, papel, fonte }
ambiguidade / motivos[] / parser_versao
```

A gramática reconhece posição da ação principal, coordenação, finalidade,
complementos e exclusões. O léxico não funciona como regex de família em qualquer
posição. Um núcleo desconhecido não autoriza buscar outra palavra conveniente.
Descrição específica prevalece; o objeto geral nunca substitui descrição ausente.
Naturezas coordenadas sem predominância demonstrável resultam em revisão.

Esta é uma gramática deliberadamente limitada, não um motor de compreensão
irrestrita de português. Fora da cobertura reconhecida, abstém-se. A eficácia
em descrições reais, além dos contrastes certificados, depende do Gate C.

Somente `OBRA → PEDE_GARANTIA` possui regra comercial autorizada nesta entrega.
Outras naturezas reconhecidas retornam `REGRA_GSB_PENDENTE`, não descarte nem
promoção arbitrária. Ambiguidade retorna `REVISAO`, origem `NAO_CLASSIFICADO`.
Regra de obra inferida mantém `INFERENCIA_GOVERNADA`. Não há score, percentual de
confiança ou afirmação de exigência documental. `garantia_documental=NAO_INVESTIGADA`.

## Catálogo: estrutura presente, certificação ausente

Identidade pretendida: `(catalogo_sistema, catalogo_codigo_item)`; nunca código
isolado. Nem `S`, nem `M`, nem o prefixo identificam automaticamente o catálogo.

| Camada | Campos |
|---|---|
| Recebido | `catalogo_id_raw`, `catalogo_nome_raw`, `catalogo_codigo_item_raw`, `material_ou_servico_raw`, objeto catálogo completo e categoria bruta |
| Normalização | `catalogo_sistema`, `catalogo_codigo_item`, `catalogo_validacao_status` |
| Registro oficial | `codigo_oficial`, `nome_oficial`, `classe_oficial`, `grupo_oficial`, `catalogo_snapshot_data`, `catalogo_snapshot_sha256` |
| Curadoria | `gsb_curadoria_status_raw`, `gsb_ativo_motor_raw`, `gsb_ativo_motor`, versão e fonte |
| Decisão | `classificacao_origem`, versão do classificador e regra aplicada |

Estados válidos: `NAO_FORNECIDO`, `NAO_VALIDADO`, `MATCH_EXATO`, `SEM_MATCH`,
`CONTRADITORIO`, `ERRO_LOOKUP`. A implementação inicial só produz os dois primeiros,
pois não executa lookup não certificado. Os demais estão contratados, não simulados.
Não há emissor ativo de `CODIGO_OFICIAL` nem variável de ambiente para liberá-lo.

Após certificação: código validado + curadoria específica permite `CODIGO_OFICIAL`;
código validado sem curadoria permite evidência para `INFERENCIA_ORIENTADA`;
ausência de identidade segue `INFERENCIA_GOVERNADA`; insuficiência fica em revisão.
Essa precedência futura não é uma integração entregue neste Gate B.

`TRUE/FALSE/NULL` significam ativo explícito/inativo explícito/não decidido na
curadoria normalizada. Valores históricos brutos são preservados literalmente,
sem transformar `FALSE` histórico não curado em decisão humana. `APROVADO` não
vira `PEDE_GARANTIA` automaticamente. Nenhum `DEFAULT FALSE` foi criado.

CATMAT não foi revalidado nem utilizado. CATSER-first permanece possível após
certificação; nenhuma snapshot ou curadoria existente foi alterada.

## Persistência isolada

SQLite é exclusivamente um registro de prova, criado explicitamente por
`init-ledger` em arquivo novo. `Store` não cria schema nem aceita arquivo ausente,
sobrescrita, symlink ou base com verificação de integridade inválida.

Tabelas: `metadata`, `runs`, `pages`, `events`, `revisions`, `observations`,
`quarantine`, `candidate_cases`, `decisions`, `evaluations`. Transação por execução;
fatos/revisões/decisões imutáveis por chave e observações acrescentadas por execução.
Bytes originais de páginas são guardados, além de hashes e normalizações.

Não há migration de produção, DSN, cliente Supabase, DDL em request, importação
dos 42, e-mail, escrita comercial ou ativação de scheduler. A reversibilidade
consiste em abandonar o arquivo de prova isolado, por decisão explícita; nenhum
comando de limpeza automática é fornecido.
