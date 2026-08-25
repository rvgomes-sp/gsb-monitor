# Doutrina da Esteira, Biblioteca de Objetos e Taxonomia de Garantia

> Documento-mãe do redesenho de 24–25/08/2026. Consolida as decisões do Rodrigo.
> Onde este doc divergir de textos anteriores (ex.: parte do CHECKPOINT_2026-08-24),
> **este prevalece** — ver §8 (reconciliação).

## 1. A metáfora operacional (doutrina Rodrigo)

- **PNCP = dragagem.** Extrai bruto, barato, sem filtrar na API.
- **Supabase = esteira vibratória.** Separa pedra de ouro em SQL, na NOSSA base.
- **Monitor = ambiente das oportunidades.** Só recebe **ouro completo**. Nunca uma
  linha sem os dados disponíveis (comprador, vencedor, valor estimado, valor
  homologado, regra dos 85% para obra, data do resultado, delta/frescor, fonte/safra).
  O que não estiver disponível, **registra-se no banco e não sobe** ao monitor.

## 2. Duas camadas (a chave de tudo)

| Camada | Filtro | Volume/dia | Superfície | Papel |
|---|---|---|---|---|
| **BIBLIOTECA** | `valorTotalEstimado ≥ 10 MM` | ~260–280 | Consulta (barato) | Universo/vigília. Classifica objeto+garantia. Nada se descarta. |
| **OURO (ESTEIRA)** | `valorTotalHomologado ≥ 10 MM` | ~70 | Consulta + drill Integração | Evento 7 real. Drilla, explode por vencedor/lote, sobe ao monitor. |

**Regra dura:** **EVT-007 = existe valor homologado.** Sem `valorTotalHomologado`,
não é evento 7. O estimado mede o *porte* do universo (biblioteca); o homologado
define o *ouro* (esteira/monitor). São camadas complementares, não concorrentes.

## 3. Taxonomia CNAE-like — `ID = codigo_objeto-garantia_codigo`

Ex.: `O.02-G1` (obra·pavimentação, exige garantia), `B.01-ND.A` (bem·medicamento, provável).

### Grupos (raiz)
`O` OBRA/ENGENHARIA · `S` SERVIÇO · `B` BEM/AQUISIÇÃO · `C` CONCESSÃO/PPP · `X` NÃO CLASSIFICADO

### Subgrupos
O.01 Edificação · O.02 Pavimentação · O.03 Saneamento · O.04 Rodovia · O.05 Elétrica ·
O.06 Arte especial · O.07 Serviço de engenharia (inclui fiscalização/supervisão de obra) ·
S.01 Serviço contínuo c/ mão de obra · S.02 TI/software · S.03 Serviço diverso ·
S.04 Locação · S.05 Serviço financeiro (folha/banco) ·
B.01 Medicamento/saúde · B.02 Alimentação · B.03 Combustível · B.04 Veículo/máquina ·
B.05 Equipamento/mobiliário · B.06 Material/insumo · C.01 Concessão/PPP · X.00 A enriquecer.

### Garantia (eixo cruzado)
`G0` Certeza · `G1` Exige (status **EXIGE**, confirmado). Incerto → status **ND**
(Não Identificado), mas guarda a qualificação inicial, que dá a **prioridade de
consulta ao edital**: `ND.A` Provável (1) · `ND.B` Possível (2) · `ND.C` Depende (3) ·
`ND.D` Improvável (4) · `ND.Z` Sem qualificação (9). **Nada se descarta.**

## 4. Regras de garantia (verdade do Rodrigo — golden set 21/08)

1. **Valor + tipo de produto** elevam garantia: medicamento/insumo saúde SRP de alto valor = **Provável** (não improvável).
2. **Fornecimento + instalação/mão de obra** (ex.: ar-condicionado com instalação) → **Possível/Provável**.
3. **Alimentação preparada no local** = serviço → **Provável**; só fornecimento de gêneros sem preparo → **Improvável**.
4. **Uniformes / material escolar** (fornecimento parcelado) → **Provável**.
5. **Combustível** → **Provável**, porém "de difícil aceitação" (volatilidade de preço) — nuance de subscrição.
6. **Concessão / PPP** → **Certeza** (a concessão é a 1ª garantia; melhorias depois com performance).
7. **Engenharia / serviço de engenharia** → **Exige**.
8. **Serviço contínuo c/ dedicação de mão de obra** → **Exige**.
9. **Fiscalização / supervisão / gerenciamento de obra** → serviço de engenharia, **Exige**.

Disciplina (freeze): nova regra do classificador só nasce de **erro observado**, virando caso de golden set.

## 5. Regra dos 85% (só família O)

No instante da homologação temos estimado E homologado. Para **obra**, quando
`valor_homologado < 85% do valor_estimado` (deságio > 15%, Lei 14.133 art. 59 §5º),
cabe **garantia adicional/reforçada** → flag `garantia_reforcada = true`. É oportunidade
de garantia *maior*. Calculada no consolidado; refinável por lote no drill.

## 6. Frescor e grão

- **Frescor = `dataResultado − dataInclusao`** (delta), por fonte/safra. `FRESH` (Δútil ≤ 1),
  `FRESH_CALENDAR_EXCEPTION` (sex→seg), `BACKFILL` (homologação antiga aflorando).
- **Grão do ouro = 1 vencedor × 1 lote = 1 contrato = 1 garantia.** Múltiplos vencedores
  do mesmo certame, ou lotes distintos, geram **uma linha cada**.
- **Regra dos itens:** no drill, até 10 itens, soma > R$ 10 MM.

## 7. O que sobe ao monitor

Só **frescas**, grupos **O e S** (obras e serviços), ouro completo, ordenado
**frescor → valor homologado**, com 85% sinalizado. Rota: > R$ 10 MM Corretora VF /
≤ R$ 10 MM Consultoria VM. B/medicamentos e ND aguardam a fase de edital no banco.
Backfill e incompletos ficam no banco, auditáveis — não sobem.

## 8. Reconciliação com o CHECKPOINT_2026-08-24

O checkpoint (manhã) tratou `valorTotalHomologado` como "quase sempre nulo" e os
"69/dia" como artefato de funil. A decisão final (noite) resolve por **duas camadas**:
o funil ÚNICO era o erro; separando **biblioteca (estimado, universo ~263)** de
**ouro (homologado, evento 7 ~70)**, os ~70/dia **são o ouro correto**, não um artefato.
Ambos os textos valem no que descrevem; onde houver conflito sobre o filtro, **vale este doc**.

## 9. Mapa dos arquivos (pipeline)

| Arquivo | Papel |
|---|---|
| `coletor/ingest_consulta.py` | Dragagem barata (Consulta, mod 4-7) → `saidas/raw_AAAAMMDD.json` |
| `coletor/carrega_base.py` | Gera SQL de carga do universo ≥10MM |
| `ferramentas/classificador_biblioteca.py` | Classificador objeto→ID (taxonomia + 9 regras de garantia) |
| `ferramentas/biblioteca_objetos.py` | Gera a planilha de rotulagem humana (golden) |
| `ferramentas/processa_dia_biblioteca.py` | Classifica um dia (máquina) → `gsb.biblioteca_objetos` |
| `coletor/esteira_evt007.py` | Homologado≥10MM → drill O/C/S → explode lote → `gsb.oportunidades_evt007` |
| `monitor/subir_ouro.py` | Sobe frescas O+S ao monitor (POST /api/import/snapshot) |
| `banco/030_*`, `banco/031_*` | DDL do schema `gsb` (biblioteca, taxonomia, ouro) |

Base Supabase: projeto **observatorio-sg** (`pjghkqqrbcjmcvujwunf`), schema `gsb`.
Credenciais só em `monitor-vip/.env.local` (git-ignored) — nunca no código.
