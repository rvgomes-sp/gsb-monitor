[TRILHA: CURADOR → B.MENTOR]
[TIPO: ENTREGA — MIC-002 / ETAPA 1]

MAIN_BASE_SHA: 379aa408eb7e4e4b524b9ee25d254a3535a6a91a
BRANCH: feat/mic-002-autonomo-v01
IMPLEMENTATION_COMMIT: 765720d96dcf2caebb3a179f06588719583b296f
BRANCH_HEAD_SHA: informado no checkpoint de entrega após inclusão deste documento e do manifesto

PATHS ALTERADOS

- mic/__init__.py
- mic/catalog.py
- mic/contracts.py
- mic/engine.py
- mic/evidence.py
- mic/repository.py
- mic/run.py
- tests/test_mic_architecture.py
- tests/test_mic_engine.py
- tests/test_mic_evidence.py
- tests/test_mic_repository.py
- supabase/migrations/20260915063000_mic_autonomous_v01.sql
- governanca/MIC_002_ETAPA1_CHECKPOINT.md
- governanca/MIC_002_ETAPA1_HASHES.sha256
- governanca/MIC_002_ETAPA1_ORDEM.md
- governanca/MIC_002_ETAPA1_TESTES.log
- governanca/MIC_ORIGENS_REUSO_v0.1.md

PATHS_PROIBIDOS_ALTERADOS: NÃO.

ARQUITETURA MIC

O MIC recebe registros factuais por injeção, agrupa por `[case_id,item_number]`, adquire uma evidência oficial por item através de interface abstrata, valida o SHA-256 sobre os bytes antes do JSON, preserva campos raw e seus nomes oficiais, aplica regra literal de namespace configurada e executa lookup exato em snapshots injetados. O repository separa SELECT futuro de `gsb.evt007_results` de INSERT futuro exclusivamente em `gsb.mic_runs` e `gsb.mic_identity_observations`.

DEPENDENCIA_MOTOR: NÃO.
DEPENDENCIA_COLETOR: NÃO.
DEPENDENCIA_MONITOR: NÃO.

MIGRATION: supabase/migrations/20260915063000_mic_autonomous_v01.sql. O Supabase CLI não estava instalado; o timestamp UTC foi registrado manualmente. A migration contém somente as duas tabelas MIC, seus índices, constraints, RLS, revokes e grants limitados ao service_role.

TABELAS_PREVISTAS:
- gsb.mic_runs
- gsb.mic_identity_observations

MIGRATION_CRIADA: SIM.
MIGRATION_APLICADA: NÃO.
SUPABASE_ESCRITO: NÃO.
SUPABASE_RUNTIME_ACESSADO: NÃO.
REDE_EXTERNA_ACESSADA PELO MIC/TESTES: NÃO. O GitHub foi acessado exclusivamente para criar a branch e versionar os artefatos autorizados.

TAXONOMIA MIC

MATCH_EXATO_CATMAT; MATCH_EXATO_CATSER; CODIGO_AUSENTE; NAMESPACE_NAO_COMPROVADO; CODIGO_OFICIAL_NAO_LOCALIZADO; IDENTIDADE_NAO_RESOLVIDA; ERRO_TECNICO.

LOOKUP_EXATO: SIM.
FALLBACK_TEXTUAL: NÃO.
DEDUP_ITEM: uma aquisição por `case_id + item_number` dentro da execução lógica; `result_key` serve apenas como proveniência.
PRESERVACAO_BYTES: URL, HTTP status, bytes, SHA-256, JSON, início, término e erro previstos no envelope de transporte. O hash é conferido antes do parse.
SHA256: teste com bytes idênticos e alteração de um byte aprovado.

TESTES: `python3 -m unittest discover -s tests -p 'test_mic_*.py' -v`.
TESTES_APROVADOS: 26.
TESTES_FALHOS: 0.

A suíte cobre T01–T21, colisão de namespace, nomes distintos dos campos raw, dois campos de código simultâneos com falha fechada, separação do repository e ausência de imports congelados, rede ou banco real.

ORIGENS_REUSO: governanca/MIC_ORIGENS_REUSO_v0.1.md. A referência histórica foi `feat/evt007-catalog-bridge-v1@0a6a89c67146e275e33735484ac6d17d7016add6`; nenhum commit foi transplantado.

DIFF MAIN: somente os 17 arquivos listados; 100% dentro da allowlist. Zero removidos e zero arquivos preexistentes modificados.
MANIFESTO_HASHES: governanca/MIC_002_ETAPA1_HASHES.sha256.

LIMITAÇÕES

- evt007_results permanece vazio;
- não houve integração real;
- não houve consulta real de identidade;
- não houve persistência real;
- não houve validação operacional.

ESTADO: IMPLEMENTADO.
TESTADO_OFFLINE: SIM.
VALIDADO: NÃO.
CERTIFICADO: NÃO.

ROLLBACK: abandonar a branch; nenhuma compensação de banco é aplicável.
OCORRÊNCIAS: Supabase CLI ausente; migration nomeada manualmente. Nenhuma ocorrência funcional ou violação de path.

PARE.
