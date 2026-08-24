# Revisão dos Endpoints — EVT-007 (PNCP API v1 / Manual v2.5)

> **Fonte:** Manual de Integração do PNCP **v. 2.5** (`manual/manual_integracao_pncp_v2.5.html`) + OpenAPI oficial v1
> baixado em 2026-08-24 (`openapi/openapi_pncp_consulta_v1.json`, `openapi/openapi_pncp_integracao_v1.json`).
> **Método:** contrato conferido **ao vivo** contra a API real (não a documentação isolada). Onde manual e realidade divergem, vale a realidade — e está anotado.
> **Escopo:** o EVT-007 é **só CONSULTA** (resultado da compra + vencedor). Nunca incluir/excluir/retificar.

---

## 1. São DUAS APIs v1 — o EVT-007 cruza as duas

| API | Base | Paths | Serve para nós |
|-----|------|-------|----------------|
| **Consulta** | `https://pncp.gov.br/api/consulta` | 12 | **Descoberta** por data + **10.5 detalhe do caso (GET)** |
| **Integração** | `https://pncp.gov.br/api/pncp` | 109 | **Itens (10.13)**, **Resultados (10.17)**, **Documentos (10.8/10.9)** |

**Por que 301 na 10.5 pela Integração?** Na API de Integração, `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}` **não existe** — o path só expõe `PUT/DELETE/PATCH` (as plataformas *operam* a compra por aí). O `GET` do caso vive na API de **Consulta**. Confirmado no OpenAPI e ao vivo (301 na Integração, 200 na Consulta).

A API de Integração tem 109 rotas de incluir/retificar/excluir (compras, itens, resultados, documentos, atas, contratos, imagens…) — **nada disso nos interessa**. Usamos exatamente 3 rotas de leitura dela.

---

## 2. O caminho canônico do EVT-007 — 4 GETs

Todos verificados ao vivo em 2026-08-24 (caso-teste `83102277000152 / 2026 / 442`).

### Passo 1 — DESCOBERTA (API Consulta)
```
GET /api/consulta/v1/contratacoes/atualizacao
    ?dataInicial=AAAAMMDD&dataFinal=AAAAMMDD
    &codigoModalidadeContratacao={4|5|6|7}
    &pagina={n}&tamanhoPagina=50
```
- **Envelope:** `{ data:[...], totalRegistros, totalPaginas, numeroPagina, paginasRestantes, empty }`.
- `tamanhoPagina=50` é o teto (o PNCP rejeita >50 com HTTP 400).
- Filtra por **data de atualização** da contratação. Cada linha já traz o caso quase inteiro:
  `valorTotalEstimado`, **`valorTotalHomologado`**, `numeroControlePNCP`, `modalidadeId/Nome`,
  `situacaoCompraId/Nome`, `objetoCompra`, `srp`, `orgaoEntidade{cnpj,razaoSocial,poderId,esferaId}`,
  `unidadeOrgao{municipioNome,ufSigla,...}`, `usuarioNome` (plataforma de origem),
  `dataInclusao`, `dataAtualizacao`, **`dataAtualizacaoGlobal`**, `tipoInstrumentoConvocatorioNome`.
- Variante `GET /v1/contratacoes/publicacao` filtra por **data de publicação** (relevante p/ a decisão da rede de datas — §5).

### Passo 2 — DETALHE DO CASO / 10.5 (API Consulta) — *opcional*
```
GET /api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}
```
- **Envelope:** objeto (dict). Traz **`valorTotalHomologado`** autoritativo no nível do caso, `amparoLegal`, `fontesOrcamentarias`, `dataAtualizacaoGlobal`, etc.
- **Na prática pode ser dispensável:** a descoberta (Passo 1) já devolve `valorTotalHomologado` e todos os campos do caso. A 10.5 serve como *refetch* autoritativo por caso quando quisermos o snapshot mais fresco. **Decisão em aberto (§5).**

### Passo 3 — ITENS / 10.13 (API Integração)
```
GET /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens
```
- **Envelope AO VIVO: LISTA CRUA** `[...]` — *o manual diz `{itens:[...]}`, mas a API devolve array direto.* Vale a realidade.
- Suporta `?pagina=&tamanhoPagina=` (há `/itens/quantidade` para saber o total). **Não truncar** — paginar até o fim.
- Campos por item (padrão do documento): `numeroItem`, `materialOuServico(M/S)/Nome`, `descricao`,
  `quantidade`, `valorUnitarioEstimado`, `valorTotal` (estimado do item — base do 85%),
  `criterioJulgamentoNome`, **`temResultado`** (ponte p/ 10.17), `itemCategoriaId/Nome`,
  `catalogoCodigoItem`, `catalogo{id,nome}`, `categoriaItemCatalogo{id,nome}`, `ncmNbsCodigo`, `unidadeMedida`,
  `situacaoCompraItemNome`, `orcamentoSigiloso`.
  > Atenção: `catalogo` e `categoriaItemCatalogo` são **objetos**, não texto (o coletor antigo lia como texto — bug a corrigir).

### Passo 4 — RESULTADOS / 10.17 (API Integração) — *o coração do EVT-007*
```
GET /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados
```
- **Envelope AO VIVO: LISTA CRUA** `[...]` — *o manual diz `{listaResultados:[...]}`, mas a API devolve array direto.*
- Campos por resultado (padrão do documento): **`dataResultado`** (marco), **`dataInclusao`** (entrada no PNCP),
  `sequencialResultado`, `quantidadeHomologada`, `valorUnitarioHomologado`,
  **`niFornecedor`** (CNPJ/CPF — pode ser alfanumérico), `nomeRazaoSocialFornecedor`, `tipoPessoa` (PJ/PF/PE),
  **`porteFornecedorId`** (1-ME, 2-EPP, **3-Demais**, 4-N/A, 5-Não informado) `/porteFornecedorNome`,
  **`naturezaJuridicaId`/`naturezaJuridicaNome`**, `codigoPais`,
  `situacaoCompraItemResultadoId/Nome`, `dataCancelamento`, `motivoCancelamento`,
  `indicadorSubcontratacao`, `ordemClassificacaoSrp`, `reservaRemanescente{codigo,nome}`, `localidadeFornecedor{...}`.
- **`valorTotalHomologado` NÃO existe aqui.** Total do item = `quantidadeHomologada × valorUnitarioHomologado` (calculado por nós). Total do caso = `valorTotalHomologado` da 10.5/descoberta.

### (Motor de editais) — DOCUMENTOS / 10.8 + 10.9 (API Integração)
```
GET  /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos            # lista
GET  {url do item}                                                             # baixa
```
- **Envelope AO VIVO: LISTA CRUA** de documentos: `titulo`, `tipoDocumentoNome` (ex. "Edital"), `tipoDocumentoId`,
  `sequencialDocumento`, `dataPublicacaoPncp`, **`url`/`uri`** de download.
- O download é servido de `https://pncp.gov.br/pncp-api/v1/orgaos/.../arquivos/{seq}` (host `/pncp-api/`, não `/api/pncp/`).

---

## 3. BrasilAPI está fora — porte e natureza vêm do 10.17

`porteFornecedorId/Nome` e `naturezaJuridicaId/Nome` são **campos nativos do resultado (10.17)**.
Não há motivo para BrasilAPI (fonte externa, quebra a regra de fonte única, e gravava o *nome* da natureza no campo de *id*).

**Porém — verificado ao vivo:** esses campos **vêm vazios com frequência**. No caso-teste real:
`porteFornecedorId=5 (Não Informado)`, `naturezaJuridicaId=None`. Logo a governança **"ausência de campo
não aprova nem descarta automaticamente"** é concreta: porte/natureza qualificam quando presentes; quando
ausentes, o caso segue para triagem, não é descartado nem aprovado só por isso.

---

## 4. Regras EVT-007 simples (cravadas com Rodrigo em 2026-08-24)

- **Valor:** total **> R$ 10 MM** (homologado é o que qualifica/roteia; estimado só na descoberta).
- **Modalidades:** 4, 5, 6, 7.
- **Sempre COM resultado** (tem `dataResultado`/`temResultado`).
- **Máx. 10 itens por caso** (contrato grande = muitos itens pequenos).
- **Todas as fontes de compra** (não só compras.gov) — é o que a descoberta do PNCP já entrega.
- **Famílias comerciais** (qualificam): **obras, fornecimento de mão de obra, locação de veículos, transporte público.**
- **Demais itens** do catálogo de serviços/compras → **status "monitorado"** (ficam visíveis, não são o alvo comercial).
- **Fornecedor:** CPF (pessoa física) descartado; CNPJ pode ser alfanumérico (Receita 2026).
  Porte "Demais" (id 3) e natureza SA aberta (2046)/fechada (2054)/Ltda (2062)/Ltda unipessoal **quando presentes**.
- **Situação:** cancelado/revogado/suspenso/deserto/fracassado → só evidência/auditoria, fora da base comercial.
- **Gatilho 85%** (homologado/estimado < 0,85 → garantia adicional provável): **somente itens de obra.**

---

## 6. Seleção de campos confirmada (Rodrigo, 2026-08-24)

### 10.5 / Descoberta — campos do caso a persistir
| ID | Campo | ID | Campo |
|----|-------|----|-------|
| 1 | numeroControlePNCP | 14 | informacaoComplementar |
| 2 | numeroCompra | 15 | srp |
| 3 | anoCompra | 20 | **valorTotalHomologado** |
| 7 | modalidadeId | 27 | orgaoEntidade |
| 8 | modalidadeNome | 27.1 | orgaoEntidade.cnpj |
| 9 | modoDisputaId | 27.2 | orgaoEntidade.razaoSocial |
| 10 | modoDisputaNome | 31 | usuarioNome (plataforma) |
| 11 | situacaoCompraId | 32 | linkSistemaOrigem |
| 12 | situacaoCompraNome | 35 | dataAtualizacaoGlobal |
| 13 | objetoCompra | | |

> Nota: **UF/município** (10.5 id 28 `unidadeOrgao`) não foi marcado aqui porque já vem na **descoberta** — fonte única, sem GET redundante. `sequencialCompra` (id 26) é derivado da descoberta. `valorTotalEstimado` (id 19) fica só na descoberta (filtro), não na 10.5.

### 10.17 — campos do resultado a persistir
| ID | Campo | ID | Campo |
|----|-------|----|-------|
| 1 | listaResultados (a lista) | 1.10 | porteFornecedorNome |
| 1.1 | numeroItem | 1.11 | naturezaJuridicaId |
| 1.2 | sequencialResultado | 1.12 | naturezaJuridicaNome |
| 1.3 | quantidadeHomologada | 1.13 | codigoPais |
| 1.4 | **valorUnitarioHomologado** | 1.14 | indicadorSubcontratacao |
| 1.6 | tipoPessoa (PJ/PF/PE) | 1.16 | dataResultado |
| 1.7 | niFornecedor | 1.17 | dataCancelamento |
| 1.8 | nomeRazaoSocialFornecedor | 1.19 | situacaoCompraItemResultadoId |
| 1.9 | porteFornecedorId | 1.20 | situacaoCompraItemResultadoNome |
| 1.10 | porteFornecedorNome | 1.21 | dataInclusao |
| 1.11 | naturezaJuridicaId | | |
| 1.12 | naturezaJuridicaNome | | |

> **Confirmado (Rodrigo, 2026-08-24):** incluídos **1.4 `valorUnitarioHomologado`** (fecha `qtd × unitário` =
> total homologado do item, ranking dos 10 maiores e ratio do gatilho 85%) e **1.19/1.20
> `situacaoCompraItemResultado`** + **1.17 `dataCancelamento`** (tiram cancelado/desclassificado da base
> comercial, mantendo em evidência). **Calculado por nós:** `valorTotalHomologado_item = 1.3 × 1.4`.

### Participantes — "banco vivo"
Persistir **todas** as linhas de `listaResultados` por item (não só a 1ª): quando o item tem vários
`sequencialResultado`, capturamos cada fornecedor classificado. **Investigação pendente:** confirmar ao vivo
se o PNCP lista também os **desclassificados/perdedores** ou só classificados/homologados — define até onde o
"todos que concorreram" é alcançável pela 10.17.

---

## 5. Decisões — fechadas e pendentes

**FECHADAS:**

1. **Rede de datas — guardar as DUAS, sem fundir.** Persistimos `dataResultado` **e** `dataInclusao` em toda
   linha. Justificativa factual: no manual, `dataInclusao` (10.17 id 1.21) é a **data de inclusão do registro**
   (estável); quem se move por eventos subsequentes é `dataAtualizacao` (id 1.22) — logo a inclusão não "anda".
   No teste com compras.gov o delta era **zero**; guardar as duas revela o delta por fonte de compra e cobre o
   caso de resultado incluído com atraso. `dataResultado` e `dataInclusao` **nunca fundidas** (governança).
2. **Homologação — resolvido.** A descoberta já devolve `valorTotalHomologado` (homologação sem GET extra).
   10.5 fica como *refetch* autoritativo opcional. **Sempre trabalhamos com o dia D.**
3. **Backend:** **Postgres/Supabase** — motor diário: coleta → grava → qualifica → sobe ao monitor. **Banco vivo.**
4. **Módulos independentes:** coletor, **leitura de editais** e **enriquecimento comercial** são motores
   separados (servem outros monitores da VF_Intelligence_Platform) — não acoplados a este monitor.
5. **Monitor atual = teste antigo → zerar.** O `monitor_feed_real.json` de 12/08 é teste e será descartado.
6. **Primeira coleta real = D-1** (para medir volume antes de cravar o modelo de serviços/materiais).

7. **10.17 campos — resolvido.** Incluídos `valorUnitarioHomologado` (1.4), `situacaoCompraItemResultado`
   (1.19/1.20) e `dataCancelamento` (1.17). Ver §6.
8. **Gatilho 85% — confirmado: SOMENTE obras.** `ratio_85 = valorTotalHomologado_item ÷ valorTotal_item(estimado)`
   calculado e avaliado **apenas** para itens da família *obras*; nas demais famílias não se aplica.

**PENDENTE:**

9. **Participantes:** confirmar ao vivo se o PNCP expõe desclassificados/perdedores ou só classificados/homologados
   (define o alcance do "banco vivo com todos que concorreram").
