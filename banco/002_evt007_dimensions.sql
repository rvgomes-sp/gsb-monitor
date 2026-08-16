CREATE TABLE IF NOT EXISTS gsb.evt007_suppliers (
    supplier_identifier text PRIMARY KEY,
    supplier_name text,
    person_type text,
    country_code text,
    supplier_size_id integer,
    supplier_size_name text,
    legal_nature_id text,
    legal_nature_name text,
    subcontracting_indicator text,
    source_name text NOT NULL,
    source_payload jsonb NOT NULL,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

WITH latest_supplier AS (
    SELECT DISTINCT ON (supplier_identifier)
        supplier_identifier,
        supplier_name,
        source_payload ->> 'tipoPessoa' AS person_type,
        source_payload ->> 'codigoPais' AS country_code,
        supplier_size_id,
        supplier_size_name,
        legal_nature_id,
        legal_nature_name,
        source_payload ->> 'indicadorSubcontratacao' AS subcontracting_indicator,
        source_name,
        source_payload,
        first_seen_at,
        last_seen_at
    FROM gsb.evt007_results
    WHERE supplier_identifier IS NOT NULL
      AND supplier_identifier <> ''
    ORDER BY supplier_identifier, last_seen_at DESC, result_key
)
INSERT INTO gsb.evt007_suppliers (
    supplier_identifier,
    supplier_name,
    person_type,
    country_code,
    supplier_size_id,
    supplier_size_name,
    legal_nature_id,
    legal_nature_name,
    subcontracting_indicator,
    source_name,
    source_payload,
    first_seen_at,
    last_seen_at
)
SELECT
    supplier_identifier,
    supplier_name,
    person_type,
    country_code,
    supplier_size_id,
    supplier_size_name,
    legal_nature_id,
    legal_nature_name,
    subcontracting_indicator,
    source_name,
    source_payload,
    first_seen_at,
    last_seen_at
FROM latest_supplier
ON CONFLICT (supplier_identifier) DO UPDATE SET
    supplier_name = excluded.supplier_name,
    person_type = excluded.person_type,
    country_code = excluded.country_code,
    supplier_size_id = excluded.supplier_size_id,
    supplier_size_name = excluded.supplier_size_name,
    legal_nature_id = excluded.legal_nature_id,
    legal_nature_name = excluded.legal_nature_name,
    subcontracting_indicator = excluded.subcontracting_indicator,
    source_payload = excluded.source_payload,
    last_seen_at = GREATEST(gsb.evt007_suppliers.last_seen_at, excluded.last_seen_at);

CREATE TABLE IF NOT EXISTS gsb.evt007_item_enrichment_queue (
    case_id text PRIMARY KEY,
    organization_cnpj text NOT NULL,
    procurement_year integer NOT NULL,
    procurement_sequence integer NOT NULL,
    status text NOT NULL DEFAULT 'PENDING',
    attempts integer NOT NULL DEFAULT 0,
    source_endpoint text,
    expected_items integer,
    collected_items integer NOT NULL DEFAULT 0,
    last_http_status integer,
    last_error text,
    started_at timestamptz,
    finished_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'RETRY', 'ERROR'))
);

WITH parsed_cases AS (
    SELECT
        case_id,
        regexp_match(case_id, '^([0-9]{14})-1-([0-9]+)/([0-9]{4})$') AS parts
    FROM (
        SELECT DISTINCT case_id
        FROM gsb.evt007_results
    ) cases
)
INSERT INTO gsb.evt007_item_enrichment_queue (
    case_id,
    organization_cnpj,
    procurement_year,
    procurement_sequence
)
SELECT
    case_id,
    parts[1],
    parts[3]::integer,
    parts[2]::integer
FROM parsed_cases
WHERE parts IS NOT NULL
ON CONFLICT (case_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS gsb.evt007_items (
    item_key text PRIMARY KEY,
    case_id text NOT NULL REFERENCES gsb.evt007_item_enrichment_queue(case_id),
    item_number integer NOT NULL,
    material_or_service text,
    material_or_service_name text,
    catalog_code text,
    description text,
    quantity numeric,
    unit_of_measure text,
    estimated_unit_value numeric,
    estimated_total_value numeric,
    confidential_budget boolean,
    item_status text,
    source_name text NOT NULL,
    source_endpoint text NOT NULL,
    source_payload jsonb NOT NULL,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, item_number)
);

CREATE INDEX IF NOT EXISTS evt007_items_case_idx
    ON gsb.evt007_items(case_id);
CREATE INDEX IF NOT EXISTS evt007_items_type_idx
    ON gsb.evt007_items(material_or_service);
CREATE INDEX IF NOT EXISTS evt007_items_catalog_code_idx
    ON gsb.evt007_items(catalog_code);

CREATE OR REPLACE VIEW gsb.evt007_results_enriched AS
SELECT
    result.*,
    item.material_or_service,
    item.material_or_service_name,
    item.catalog_code,
    item.description AS item_description,
    CASE
        WHEN item.item_key IS NULL THEN 'NAO_ENRIQUECIDO'
        WHEN item.material_or_service = 'M' THEN 'MATERIAL'
        WHEN item.material_or_service = 'S' THEN 'SERVICO'
        ELSE 'DEMAIS'
    END AS technical_classification
FROM gsb.evt007_results result
LEFT JOIN gsb.evt007_items item
  ON item.case_id = result.case_id
 AND item.item_number = result.item_number;

CREATE OR REPLACE VIEW gsb.evt007_materials AS
SELECT *
FROM gsb.evt007_results_enriched
WHERE technical_classification = 'MATERIAL';

CREATE OR REPLACE VIEW gsb.evt007_services AS
SELECT *
FROM gsb.evt007_results_enriched
WHERE technical_classification = 'SERVICO';

CREATE OR REPLACE VIEW gsb.evt007_other_items AS
SELECT *
FROM gsb.evt007_results_enriched
WHERE technical_classification IN ('DEMAIS', 'NAO_ENRIQUECIDO');
