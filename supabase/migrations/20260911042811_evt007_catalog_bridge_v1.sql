-- 003-S / 02-R / Etapa 2. Requires factual baseline migration.
DO $$
BEGIN
  IF to_regclass('gsb.evt007_results') IS NULL THEN
    RAISE EXCEPTION 'Missing canonical gsb.evt007_results; stop and resolve destination';
  END IF;
END $$;

CREATE TABLE gsb.evt007_item_identity (
  item_key text PRIMARY KEY,
  case_id text NOT NULL,
  item_number integer NOT NULL CHECK (item_number > 0),
  id_contratacao_pncp text,
  id_compra text,
  id_compra_item text,
  material_ou_servico_raw jsonb,
  cod_item_catalogo_raw jsonb,
  catalog_namespace text CHECK (catalog_namespace IN ('CATSER','CATMAT')),
  catalog_code text,
  catalog_match_status text NOT NULL CHECK (catalog_match_status IN (
    'CATSER_MATCH_EXATO','CATSER_NAO_LOCALIZADO','MATERIAL_PRESERVADO',
    'CODIGO_CATALOGO_AUSENTE','NAMESPACE_NAO_RESOLVIDO',
    'AQUISICAO_IDENTIDADE_FALHOU','ERRO_TECNICO_CATALOGO')),
  catalog_name text,
  catalog_group_code text,
  catalog_group_name text,
  identity_source text NOT NULL,
  identity_endpoint text,
  identity_payload_hash text CHECK (identity_payload_hash IS NULL OR length(identity_payload_hash)=64),
  identity_acquired_at timestamptz,
  catalog_snapshot_sha256 text,
  bridge_version text NOT NULL,
  identity_payload jsonb,
  raw_field_presence jsonb NOT NULL,
  failure_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(case_id,item_number),
  CHECK (item_key = '[' || to_json(case_id)::text || ',' || item_number::text || ']'),
  CHECK (catalog_match_status <> 'MATERIAL_PRESERVADO' OR
    (catalog_namespace IS NOT DISTINCT FROM 'CATMAT' AND material_ou_servico_raw IS NOT DISTINCT FROM '"M"'::jsonb)),
  CHECK (catalog_match_status NOT IN ('CATSER_MATCH_EXATO','CATSER_NAO_LOCALIZADO') OR
    (catalog_namespace IS NOT DISTINCT FROM 'CATSER' AND material_ou_servico_raw IS NOT DISTINCT FROM '"S"'::jsonb
    AND catalog_code IS NOT NULL AND catalog_snapshot_sha256 IS NOT DISTINCT FROM
    'f3cd884220115be97fd7782a25e799d8c64390786794d27c3fef53806e67f264'))
);
ALTER TABLE gsb.evt007_item_identity ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON gsb.evt007_item_identity FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON gsb.evt007_item_identity TO service_role;

-- Immutable per-run observations preserve future divergence without replacing history.
CREATE TABLE gsb.evt007_item_identity_observations (
  run_id text NOT NULL REFERENCES gsb.evt007_collection_runs(run_id),
  item_key text NOT NULL REFERENCES gsb.evt007_item_identity(item_key),
  observation jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(run_id,item_key)
);
ALTER TABLE gsb.evt007_item_identity_observations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON gsb.evt007_item_identity_observations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON gsb.evt007_item_identity_observations TO service_role;

-- This view deliberately exposes the first preserved identity, not an implicit latest.
CREATE VIEW gsb.v_evt007_classified_results WITH (security_invoker=true) AS
SELECT r.result_key,r.case_id,r.item_number,r.result_sequence,
       r.supplier_identifier,r.supplier_name,r.result_date,r.inclusion_at,
       r.homologated_quantity,r.homologated_unit_value,r.homologated_total_value,
       i.material_ou_servico_raw,i.cod_item_catalogo_raw,
       i.catalog_namespace,i.catalog_code,i.catalog_match_status,
       i.catalog_name,i.catalog_group_code,i.catalog_group_name,
       i.identity_source,i.identity_payload_hash,i.catalog_snapshot_sha256,i.bridge_version
FROM gsb.evt007_results r
LEFT JOIN gsb.evt007_item_identity i ON i.case_id=r.case_id AND i.item_number=r.item_number;
REVOKE ALL ON gsb.v_evt007_classified_results FROM PUBLIC, anon, authenticated;
GRANT SELECT ON gsb.v_evt007_classified_results TO service_role;
