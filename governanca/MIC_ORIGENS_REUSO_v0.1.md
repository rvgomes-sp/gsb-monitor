# MIC — Origens de reuso v0.1

Referência histórica consultada: `feat/evt007-catalog-bridge-v1@0a6a89c67146e275e33735484ac6d17d7016add6`. Nenhum commit dessa branch foi transplantado.

| Origem | Arquivo de origem | Conceito | Novo arquivo MIC | Adaptação | Elementos descartados |
|---|---|---|---|---|---|
| Experimento 003-S | `coletor/evt007_catalog_bridge.py` | chave determinística `[case_id,item_number]` | `mic/engine.py` | implementação própria, isolada e independente de result_key | corte econômico, CATSER fixo e persistência EVT-007 |
| Experimento 003-S | `coletor/evt007_catalog_bridge.py` | hash antes da interpretação | `mic/evidence.py` | envelope de transporte abstrato e bytes obrigatórios | urllib, rede real e diretório operacional |
| Experimento 003-S | `coletor/evt007_catalog_bridge.py` | lookup exato com snapshot validado | `mic/catalog.py` | catálogo genérico injetado por namespace | snapshot físico, fallback e taxonomia experimental |
| Experimento 003-S | `coletor/evt007_catalog_bridge.py` | M/S literal | `mic/engine.py` | regra explicitamente configurada e versionada | certificação implícita e normalização |
| Experimento 003-S | `coletor/evt007_catalog_bridge.py` | uma aquisição por item | `mic/engine.py` | agrupamento item-cêntrico antes do transporte | grão por resultado e consultas repetidas |
| Migration experimental | `supabase/migrations/20260911042811_evt007_catalog_bridge_v1.sql` | observação imutável por execução | `supabase/migrations/20260915063000_mic_autonomous_v01.sql` | tabelas exclusivas `mic_*` | escrita em `evt007_item_identity*`, view e taxonomia experimental |

O MIC não importa módulos de `coletor`, `motor` ou `monitor`. A referência preserva conhecimento técnico; não promove a implementação experimental.
