# EVT-007 — Classificação de Item (regra experimental v1)

> **Status:** EXPERIMENTAL. Baseada em evidência empírica parcial (2026-08-25).
> Permanece experimental até **validação multissafra e multiplataforma**.
> Ferramentas de aferição: `ferramentas/assinatura_itens.py`, `ferramentas/perfil_temporal.py`.

## Evidência (recorte testado)

Amostra: **17 contratações, 83 itens**, tier **> R$ 10 MM**, modalidades 4/5/6/7, dia 2026-08-20.

| Campo | present_key | non_null |
|---|---|---|
| `catalogoCodigoItem` | 100% | **0%** |
| `catalogo` | 100% | **0%** |
| `categoriaItemCatalogo` | 100% | **0%** |
| `ncmNbsCodigo` | 100% | **0%** |
| `ncmNbsDescricao` | 100% | **0%** |
| `informacaoComplementar` | 100% | **0%** |
| `materialOuServico` | 100% | **100%** |
| `unidadeMedida` | 100% | **100%** |
| `criterioJulgamentoNome` | 100% | **100%** |

- **Chave estrutural presente (100%), conteúdo informacional ausente (0%)**: a API entrega o schema,
  mas o sistema de origem não popula os valores neste recorte. Logo catálogo/NCM são **features
  indisponíveis**, não classificadores.
- **10.13 × 10.14:** 17/17 mesmas chaves, 0 campos extras (única divergência `imagem` 0 vs null).
  O item individual **não enriquece** → 10.14 é endpoint de **controle**, não etapa de classificação.

## Regra canônica provisória (v1)

> No recorte > R$ 10 MM testado, os campos de catálogo e NCM/NBS **não apresentaram conteúdo útil**.
> A classificação deve usar prioritariamente **`materialOuServico`, `unidadeMedida` e `descricao`**,
> com **modalidade** e **critério de julgamento** como contexto. Regra **experimental** até validação
> multissafra e multiplataforma.

### Classificador por EVIDÊNCIAS (não booleano)

Sinais por item:
- **A — natureza:** `materialOuServico` (S = candidato a obra/serviço; M = material).
- **B — unidade:** `unidadeMedida` ∈ conjunto estrutural de obra {KM, QUILÔMETRO, M2, METRO QUADRADO,
  M3, METRO, METRO LINEAR, HECTARE, "1 KM", global/empreitada}.
- **C — semântica (`descricao`):** restauração, pavimentação, recapeamento, implantação, construção,
  recuperação, drenagem, ponte, viaduto, rodovia, edificação, saneamento, terraplanagem, engenharia…
- **D — contexto:** modalidade + `criterioJulgamentoNome`.

Saída (preserva ambiguidade):
```
OBRA_FORTE     A=S ∧ B(unidade de obra) ∧ C(semântica de obra)
OBRA_PROVAVEL  A=S ∧ (B ∨ C)                       # um sinal estrutural + texto, ou unidade forte
SERVICO        A=S ∧ ¬(assinatura de obra)
MATERIAL       A=M
INCERTO        evidências insuficientes/contraditórias
```
A `descricao` **nunca decide sozinha** (não `if "obra" in descricao`): é evidência textual **ancorada**
pelos sinais estruturais A/B. `objetoCompra` é contexto auxiliar, não feature primária.

## Arquitetura (mudança obrigatória)

O filtro de obra **não roda antes de abrir os itens**. Fluxo correto:
```
contratação → itens (10.13) → assinatura de cada item → classificação → resultado (10.17) → roteamento
```
NÃO: `objetoCompra → descarta/mantém contratação` (perde contratação de objeto genérico com item que é obra).
O antigo `--so-obras` (regex sobre `objetoCompra`) e a lista `TERMOS_OBRA` como filtro pré-drill ficam **aposentados**.

## Pendente para cravar (2ª rodada)

Ampliar a aferição — **mais dias, mais plataformas, mais casos/modalidade** (~100–200 contratações,
algumas centenas de itens). Medir especialmente:
```
P(catalogo preenchido | plataforma)     # o 0% pode ser da PLATAFORMA (usuarioNome), não do valor
P(catalogo preenchido | modalidade)
P(catalogo preenchido | materialOuServico)
```
Se `Compras.gov=0%` mas `Plataforma X=74%`, a conclusão muda de "tier >10MM" para "origem não popula".
Até lá, a regra v1 vale como experimental.
