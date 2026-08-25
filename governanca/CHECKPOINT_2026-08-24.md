# CHECKPOINT — 2026-08-24
### Diagnóstico estrutural, o que o coletor enfrentou, e o redesenho para "banco vivo"

> ⚠️ **Atualização (25/08):** a conclusão de que `valorTotalHomologado` seria inservível
> foi superada. A decisão final separa **duas camadas** — biblioteca (estimado, universo)
> e ouro/esteira (homologado = EVT-007). Onde este checkpoint tratar do *filtro* de coleta,
> **vale `governanca/DOUTRINA_ESTEIRA_BIBLIOTECA.md`**.

> Pedido do Rodrigo: *"faça um checkpoint de tudo que foi feito hoje; a estrutura que temos agora; o motivo dos atrasos; os erros; as alterações nas estruturas; o que nosso coletor enfrentou?"* — e a correção de rota: *"traga para a NOSSA base e nela fazemos a análise; pra que analisar dentro da API?"*

---

## 1. A desconfiança do Rodrigo estava certa

> *"impossível em um dia de licitação no Brasil todo, objeto obras, acima de 10 milhões, termos 6 compras homologadas... estima-se que acima de 10 milhões/dia podemos chegar em 40 obras."*

Correto. **6 (na verdade 11) obras/dia é implausível** para o país das obras. O número baixo não é a realidade do Brasil — é **artefato do nosso funil**. A causa é estrutural, não de esforço.

---

## 2. O erro estrutural nº 1 — filtramos pelo campo errado, no lugar errado

O motor descobre em `/contratacoes/atualizacao` e **mantém só quem tem `valorTotalHomologado >= 10 MM`**. Dois problemas provados hoje:

- **`valorTotalHomologado` é derivado e quase sempre nulo.** O manual define: *"valor total homologado **com base nos resultados incluídos**"*. Se a plataforma não consolida o resultado no cabeçalho, vem `None`. A **primeira linha** da descoberta de 20/08 já é uma OBRA ("REFORMA E REQ...") com `valorTotalHomologado = None` e `valorTotalEstimado = 3,6 MM`.
- **A homologação não mora no cabeçalho da contratação.** Há **três** domínios de situação:
  - situação da **contratação** (`situacaoCompraId`) → quase sempre `1 = Divulgada no PNCP`;
  - situação do **item** (`situacaoCompraItemId`) → **`2 = Homologado`**, 1=Em Andamento, 3=Anulado, 4=Deserto, 5=Fracassado;
  - situação do **resultado** do item.
  A homologação real é do **item**. Filtrar por um campo consolidado do cabeçalho perde a maioria.

**Consequência:** ao exigir `valorTotalHomologado >= 10MM` na descoberta, cortamos as obras cujo homologado consolidado veio nulo — que são a maioria. Só 69 contratações passaram nesse crivo em 20/08; o universo real de obras grandes é muito maior (medição em `saidas/diag_universo_20260820.json`).

**Correção:** o porte da obra é lido pelo **`valorTotalEstimado`** (sempre presente), e a homologação pela **situação do item / resultado** — não pelo campo consolidado do cabeçalho.

---

## 3. O erro estrutural nº 2 — analisamos "dentro da API"

Fluxo atual (síncrono, por candidato):

```
descoberta (Consulta) → PARA CADA contratação: GET /itens (Integração) → classifica
   → GET /resultados (Integração) → só então decide
```

Isso faz **1–2+ chamadas na superfície Integração por candidato**. A Integração é justamente a superfície que **estrangula** (hoje: ReadTimeout de 25 s numa chamada única e fresca). Resultado: **horas de coleta** para produzir meia dúzia de linhas, com risco de bloqueio.

> Correção do Rodrigo: *"ao invés de trazermos os dados para estudo, vamos cortar e deixar solto para outros pegarem na API; isso não faz sentido."*

**Certo.** A análise não pode acontecer dentro da API. Tem que ser:

```
INGESTÃO barata (Consulta) → NOSSA BASE (Supabase/Postgres) → análise/classificação em SQL
   → o que interessa SOBE ao monitor → o resto FICA na base (cruza e retroalimenta)
```

---

## 4. O que o coletor enfrentou (atrasos e erros de hoje)

| Evento | O que era | Causa |
|---|---|---|
| Coleta de 21/08 travando | ReadTimeout 25s em `/itens` em cadeia | Superfície **Integração** estrangulada neste egress (a de Consulta ia bem — throttle é **por superfície**) |
| Carga bruta 429 | HTTP 429 na Consulta, breaker 90s | Pacing 0.3s **agressivo demais** + **dois processos** rodando juntos (erro meu de duplo-background nohup+`&`) |
| "3 horas" na sessão anterior | Coleta arrastando | Mesmo funil síncrono batendo na Integração por candidato |

Lições registradas na memória: **sondar as duas superfícies antes de coletar**; **um processo só**; **régua educada mesmo na Consulta**.

---

## 5. Alterações feitas hoje (o que mudou nas estruturas)

- **Monitor virou fila de oportunidades** (sua diretriz frescor→valor): dedup (Arapongas 287/288 = 1 alvo, "2 lotes"), ordenação frescor→valor, **objeto reduzido + inferência do trabalho** por linha, porte do vencedor e carimbo de frescor. KPIs corrigidos (5 obras / R$ 128,4 MM). Novo `monitor/inferencia.py`; `monitor/subir_obras.py` atualizado. **No ar.**
- **Diagnóstico de universo** `ferramentas/diag_universo_obra.py` (só Consulta) — mede quantas obras grandes existem de verdade por dia.
- **Memória**: `pncp-throttle-duas-superficies` (Consulta e Integração estrangulam independente).

---

## 6. Redesenho — o pipeline "banco vivo" (proposto)

**Camada 1 — Ingestão (Consulta, barata, superfície saudável).** 1×/dia varre mod 4‑7 em `/contratacoes/atualizacao` (e conferir `/contratacoes/publicacao`) e **grava TODAS as linhas cruas** na base (`licitacoes.contratacoes_raw`), sem filtrar. Campos já ricos: `objetoCompra`, `valorTotalEstimado`, `situacao*`, órgão, UF, datas, `usuarioNome` (plataforma), links.

**Camada 2 — Classificação na base (SQL, do nosso lado).** Sobre a base:
- gate de porte por `valorTotalEstimado >= 10 MM`;
- classificação **obra** pela família do **catálogo** (ver §7), com o classificador de texto como reforço/fallback;
- marca situação (item homologado) e frescor.

**Camada 3 — Drill seletivo (Integração, só nos qualificados).** Só as contratações que interessam recebem `/itens` + `/resultados`, **incrementalmente e resiliente** (fila com retry, não como trava síncrona). Grava itens/resultados/vencedores na base.

**Camada 4 — Monitor.** O que interessa sobe (triagem). O resto **permanece na base** para cruzamento e retroalimentação.

---

## 7. O catálogo da família OBRA (pedido do Rodrigo)

> *"na base, abra o catálogo da família obra de todo tipo e classifica; de pintura de fachada de escola à linha de transmissão; saneamento; recapeamento; aqui é o país das obras."*

Existe endpoint de catálogo: **Integração `/v1/catalogos` e `/v1/catalogos/{id}`**, e cada item carrega **`catalogoId` + `catalogoCodigoItem`**. O manual tem seção "catálogo por código". Plano:
1. **Baixar o catálogo** (CATMAT/CATSER via PNCP) para a base, uma vez, e isolar a **família/classe de OBRAS e serviços de engenharia** de todos os tipos.
2. Classificar item por **código de catálogo** (determinístico) — não por palavra-chave.
3. **Investigar por que o código vem nulo** em parte dos itens de obra (observação anterior: `present_key=100%`, `non_null=0%` no recorte homologado): é regra de dispensa do PNCP? é a plataforma que não envia? Se o código falta, cair no `materialOuServico` + descrição + unidade — mas o **primário passa a ser o catálogo**.

---

## 8. Os 14 eventos — onde estamos

Hoje operamos **só o EVT-007** (homologação). A inteligência que o Rodrigo quer cruza os 14 eventos (PCA → edital → disputa → homologação → contrato → aditivos...). A base viva é o que permite sair do "pingar licitação" para o cruzamento. Os endpoints para isso já estão mapeados: `/pca`, `/contratacoes/publicacao`, `/contratos`, `/atas`, histórico. **Fica como trilho, depois do EVT-007 rodar sólido.**

---

## 9. Próximos passos (ordem proposta)

1. **Criar as tabelas de ingestão** na base (`licitacoes.contratacoes_raw` + itens/resultados) — reaproveitando `banco/010_licitacoes_v1.sql`.
2. **Ingestão barata de 1 dia** (20/08) inteira na base (sem filtro), com pacing seguro.
3. **Baixar o catálogo** e isolar a família obra.
4. **Classificar na base em SQL** (porte por estimado + obra por catálogo).
5. **Drill seletivo** só nos qualificados → monitor.
6. Medir: quantas obras grandes/dia de verdade (validar a estimativa dos ~40).
```
