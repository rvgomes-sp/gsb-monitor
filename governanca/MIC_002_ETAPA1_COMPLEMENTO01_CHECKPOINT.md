[TRILHA: CURADOR → B.MENTOR]
[TIPO: ENTREGA — MIC-002 / ETAPA 1 — COMPLEMENTO 01]

MAIN_BASE_SHA: 379aa408eb7e4e4b524b9ee25d254a3535a6a91a
PREVIOUS_HEAD_SHA: fa11acafa3edf6899aabfb7af5a7fc96aa00f656
BRANCH: feat/mic-002-autonomo-v01
NEW_BRANCH_HEAD_SHA: informado no retorno formal após criação do commit
NOVO_COMMIT: informado no retorno formal após criação do commit
AMEND: NÃO
FORCE_PUSH: NÃO

PATHS ALTERADOS NO COMPLEMENTO

- mic/contracts.py
- mic/engine.py
- tests/test_mic_adversarial.py
- supabase/migrations/20260915063000_mic_autonomous_v01.sql
- governanca/MIC_002_ETAPA1_CHECKPOINT.md
- governanca/MIC_002_ETAPA1_COMPLEMENTO01_CHECKPOINT.md
- governanca/MIC_002_ETAPA1_COMPLEMENTO01_ORDEM.md
- governanca/MIC_002_ETAPA1_HASHES.sha256
- governanca/MIC_002_ETAPA1_TESTES.log

PATHS TOTAIS DIFF MAIN: 20 arquivos, todos dentro da allowlist MIC.
PATHS PROIBIDOS ALTERADOS: NÃO.

HTTP_NON_200_FAIL_CLOSED: SIM.
HTTP_REASON_CODE: ERRO_TRANSPORTE.
HTTP_ZERO_LOOKUP: SIM.

Qualquer `identity_http_status` diferente de 200 produz `ERRO_TECNICO`, preserva o envelope de evidência e retorna antes do parse e do catálogo. HTTP 404 e 500 com JSON válido foram testados adversarialmente.

NAMESPACE_CONFIG_EXATA: SIM.
ALIASES_REJEITADOS: SIM.

O construtor do MIC aceita exclusivamente `{"M":"CATMAT","S":"CATSER"}`. Mapa incompleto, chave adicional, alias, espaços, minúsculas, valor minúsculo e namespaces trocados falham antes da aquisição e do lookup.

SNAPSHOT_NAMESPACE_VALIDADO: SIM.
SNAPSHOT_NAMESPACE_DIVERGENTE_STATUS: ERRO_TECNICO.
SNAPSHOT_NAMESPACE_DIVERGENTE_REASON_CODE: SNAPSHOT_NAMESPACE_DIVERGENTE.
SNAPSHOT_DIVERGENTE_ZERO_LOOKUP: SIM.

O resolver compara literalmente o namespace selecionado e `snapshot.namespace` antes do hash, da integridade estrutural e do lookup. Não existe troca ou fallback de catálogo.

MIGRATION_ATUALIZADA: SIM, somente para incluir `SNAPSHOT_NAMESPACE_DIVERGENTE` na constraint fechada de `mic_reason_code`.
MIGRATION_APLICADA: NÃO.
SUPABASE_ACESSADO: NÃO.
SUPABASE_ESCRITO: NÃO.
REDE_EXTERNA_MIC_TESTES: NÃO.

TESTES_TOTAIS: 32.
TESTES_APROVADOS: 32.
TESTES_FALHOS: 0.
TESTES_ADVERSARIAIS_NOVOS: 6 métodos, incluindo matrizes de configurações inválidas.

LOOKUP_EXATO: SIM.
FALLBACK_TEXTUAL: NÃO.
FALLBACK_CATALOGO: NÃO.

IMPLEMENTADO: SIM.
TESTADO_OFFLINE: SIM.
VALIDADO: NÃO.
CERTIFICADO: NÃO.
ACEITE_ETAPA1: PENDENTE_BMENTOR.

MANIFESTO_SHA256: governanca/MIC_002_ETAPA1_HASHES.sha256.
OCORRÊNCIAS: três não conformidades corrigidas; nenhuma expansão funcional; nenhuma violação de path.

PARE.
