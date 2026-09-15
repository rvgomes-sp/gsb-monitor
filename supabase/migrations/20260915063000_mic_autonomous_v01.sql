-- MIC-002 Etapa 1. Prepared only; DO NOT APPLY in this stage.
CREATE TABLE gsb.mic_runs (
  mic_run_id text PRIMARY KEY,
  mic_version text NOT NULL,
  status text NOT NULL CHECK (status IN ('RUNNING','COMPLETE','COMPLETE_WITH_ERRORS','FAILED')),
  input_source text NOT NULL DEFAULT 'gsb.evt007_results' CHECK (input_source = 'gsb.evt007_results'),
  input_scope jsonb NOT NULL,
  namespace_rule_version text,
  catalog_refs jsonb,
  started_at timestamptz NOT NULL,
  finished_at timestamptz,
  metrics jsonb,
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((status = 'RUNNING' AND finished_at IS NULL) OR status <> 'RUNNING')
);

CREATE TABLE gsb.mic_identity_observations (
  mic_run_id text NOT NULL REFERENCES gsb.mic_runs(mic_run_id),
  item_key text NOT NULL,
  case_id text NOT NULL,
  item_number integer NOT NULL CHECK (item_number > 0),
  source_result_keys jsonb NOT NULL CHECK (jsonb_typeof(source_result_keys) = 'array'),
  source_name text NOT NULL,
  source_field_name text CHECK (source_field_name IN ('catalogoCodigoItem','codItemCatalogo')),
  material_ou_servico_raw jsonb,
  catalogo_id_raw jsonb,
  catalogo_nome_raw jsonb,
  catalogo_codigo_item_raw jsonb,
  catalog_namespace text CHECK (catalog_namespace IN ('CATMAT','CATSER')),
  catalog_code text,
  mic_status text NOT NULL CHECK (mic_status IN (
    'MATCH_EXATO_CATMAT','MATCH_EXATO_CATSER','CODIGO_AUSENTE',
    'NAMESPACE_NAO_COMPROVADO','CODIGO_OFICIAL_NAO_LOCALIZADO',
    'IDENTIDADE_NAO_RESOLVIDA','ERRO_TECNICO')),
  mic_reason_code text CHECK (mic_reason_code IN (
    'CONFLITO_IDENTIFICADORES','MULTIPLICIDADE_ITEM','EVIDENCIA_INSUFICIENTE',
    'HASH_DIVERGENTE','SNAPSHOT_INDISPONIVEL','SNAPSHOT_HASH_DIVERGENTE',
    'CHAVE_DUPLICADA_CATALOGO','CAMPO_RAW_INVALIDO','ESCOPO_NAMESPACE_NAO_COMPROVADO',
    'ERRO_PARSE','ERRO_TRANSPORTE')),
  resolution_method text NOT NULL,
  namespace_rule_version text,
  identity_source text,
  identity_endpoint text,
  identity_http_status integer CHECK (identity_http_status BETWEEN 100 AND 599),
  identity_payload_raw bytea,
  identity_payload_sha256 text CHECK (identity_payload_sha256 IS NULL OR length(identity_payload_sha256) = 64),
  identity_payload jsonb,
  identity_started_at timestamptz,
  identity_acquired_at timestamptz,
  catalog_snapshot_sha256 text CHECK (catalog_snapshot_sha256 IS NULL OR length(catalog_snapshot_sha256) = 64),
  catalog_snapshot_scope text CHECK (catalog_snapshot_scope = 'SNAPSHOT_ONLY'),
  catalog_name text,
  catalog_group_code text,
  catalog_group_name text,
  failure_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (mic_run_id,item_key),
  CHECK (item_key = '[' || to_json(case_id)::text || ',' || item_number::text || ']'),
  CHECK (identity_payload_raw IS NULL OR identity_payload_sha256 IS NOT NULL),
  CHECK (mic_status <> 'MATCH_EXATO_CATMAT' OR (catalog_namespace = 'CATMAT' AND catalog_code IS NOT NULL AND catalog_snapshot_sha256 IS NOT NULL)),
  CHECK (mic_status <> 'MATCH_EXATO_CATSER' OR (catalog_namespace = 'CATSER' AND catalog_code IS NOT NULL AND catalog_snapshot_sha256 IS NOT NULL)),
  CHECK (mic_status <> 'CODIGO_AUSENTE' OR catalog_code IS NULL),
  CHECK (mic_status <> 'NAMESPACE_NAO_COMPROVADO' OR catalog_namespace IS NULL),
  CHECK (mic_status <> 'CODIGO_OFICIAL_NAO_LOCALIZADO' OR (catalog_namespace IS NOT NULL AND catalog_code IS NOT NULL AND catalog_snapshot_sha256 IS NOT NULL AND catalog_snapshot_scope = 'SNAPSHOT_ONLY'))
);

CREATE INDEX mic_identity_observations_item_idx ON gsb.mic_identity_observations(case_id,item_number);
CREATE INDEX mic_identity_observations_status_idx ON gsb.mic_identity_observations(mic_status);

ALTER TABLE gsb.mic_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsb.mic_identity_observations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON gsb.mic_runs, gsb.mic_identity_observations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON gsb.mic_runs TO service_role;
GRANT SELECT, INSERT ON gsb.mic_identity_observations TO service_role;
