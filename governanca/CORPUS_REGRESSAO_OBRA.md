# Corpus de Regressão — Classificador de Obra (EVT-007)

> Golden set derivado de **12 editais reais** (pasta `Editais/`, extraídos por Rodrigo em 2026-08-25).
> Máquina: `config/corpus_regressao_obra.json`. Regra: o `classificador.py` v2 só é aceito se
> **reproduzir todos os rótulos** — preserva positivos, elimina negativos conhecidos. Evita overfitting:
> o rerun de 20/08 é validação EXTERNA, não treino.

## Matriz consolidada

| # | Objeto (resumo) | Classe esperada | Regra que testa |
|---|---|---|---|
| 1 | Construção de unidade de beneficiamento de mel + materiais e mão de obra | **POSITIVO_OBRA** | construção física + materiais + mão de obra |
| 2 | Obra rodoviária BR-158/262/MS | **POSITIVO_OBRA** | rodovia / unidade KM |
| 3 | Reforma de vestiários (engenharia) | **POSITIVO_OBRA** | reforma predial física |
| 4 | Revitalização/pavimentação de infraestrutura predial (INMETRO, SRP) | **POSITIVO_OBRA** | revitalização/pavimentação vale mesmo em pregão/SRP |
| 5 | Execução de reparos/correções em prédios escolares, empreitada | **POSITIVO_OBRA** | execução física de reparos por empreitada |
| 6 | Projetos **e posterior construção** de 150 unidades habitacionais | **POSITIVO_OBRA** | design+build (projeto + execução) |
| 7 | Construção de mercado popular, empreitada | **POSITIVO_OBRA** | construção de edificação |
| 8 | Serviços comuns de engenharia a serem realizados | **POSITIVO_ENGENHARIA_EXECUTIVA** | engenharia com execução (não só projeto) |
| 9 | **Elaboração de projeto** básico/executivo de acessibilidade (99 escolas) | **NEGATIVO_PROJETO_SEM_EXECUCAO** | 'elaboração de projeto' SEM execução/construção/integrada |
| 10 | Manutenção contínua de **praças e parques** | **NEGATIVO_SERVICO** | manutenção de praças/jardinagem = serviço contínuo |
| 11 | Manutenção **corretiva** de engenharia (NAV, SRP) | **LIMÍTROFE** | manutenção corretiva — depende de execução física/escala |
| 12 | Manutenção **predial** de bens imóveis + materiais (CINDACTA) | **LIMÍTROFE** | manutenção predial c/ materiais — sinal fraco isolado |

## Regras discriminantes que o corpus revela (para o v2)

1. **Verbo de execução física manda:** `construção / execução / reforma / revitalização / pavimentação /
   recuperação / reparos` **de** algo físico → POSITIVO. É o núcleo dos 7 positivos.
2. **⚠️ "Elaboração de projeto" isolado = NEGATIVO** (`NEGATIVO_PROJETO_SEM_EXECUCAO`). Só vira positivo se
   houver **"e posterior construção/execução"** ou **"contratação integrada"** (design+build). Esta é a regra
   que a FIOCRUZ (20/08, "elaboração de projeto básico e executivo") **falha** → era falso positivo.
3. **Aquisição de material = NEGATIVO_MATERIAL:** `aquisição de material de construção`, `registro de preços
   … material` (Horizonte/Parintins, 20/08). Verbo de **compra**, não de execução.
4. **Manutenção é ambígua e precisa de contexto:**
   - `manutenção de praças/parques/áreas verdes/jardinagem` → NEGATIVO_SERVICO.
   - `manutenção predial/corretiva de engenharia com materiais/execução` → LIMÍTROFE (não descartar, marcar p/ revisão).
5. **Cuidado com o falso reforço** (caso serralheria do histórico): `execução + material + mão de obra +
   memorial/projeto` **sozinho** não garante obra — precisa do **objeto físico de construção/infra**.

## Consequência para o `classificador.py` v2
- Camada de **verbo/objeto**: execução física de infra/edificação (POSITIVO) vs projeto-isolado / aquisição /
  manutenção-serviço (NEGATIVO).
- `objetoCompra` deixa de ser fallback frouxo por "construção"; passa a exigir **verbo de execução + objeto físico**
  e a **barrar** termos de compra/projeto-isolado.
- Saída granular: `OBRA_FORTE / OBRA_PROVAVEL / NEGATIVO / LIMÍTROFE`, com o rótulo rastreável ao sinal.
- **Aceite:** rodar `classificador` v2 contra os 12 casos → 100% de concordância nos POSITIVO/NEGATIVO;
  LIMÍTROFE pode cair em REVISAR. Só então rerun de 20/08.
