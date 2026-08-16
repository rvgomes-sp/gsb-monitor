CREATE SCHEMA IF NOT EXISTS gsb;

CREATE TABLE IF NOT EXISTS gsb.evt007_collection_runs (
    run_id text PRIMARY KEY,
    result_date date NOT NULL,
    source_name text NOT NULL,
    source_endpoint text NOT NULL,
    status text NOT NULL,
    page_size integer NOT NULL CHECK (page_size BETWEEN 10 AND 500),
    expected_pages integer,
    expected_records bigint,
    collected_pages integer NOT NULL DEFAULT 0,
    collected_records bigint NOT NULL DEFAULT 0,
    divergent_date_records bigint NOT NULL DEFAULT 0,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    error_message text
);

CREATE TABLE IF NOT EXISTS gsb.evt007_raw_pages (
    run_id text NOT NULL REFERENCES gsb.evt007_collection_runs(run_id),
    page_number integer NOT NULL CHECK (page_number > 0),
    request_url text NOT NULL,
    payload_sha256 text NOT NULL,
    payload jsonb NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, page_number)
);

CREATE TABLE IF NOT EXISTS gsb.evt007_results (
    result_key text PRIMARY KEY,
    case_id text NOT NULL,
    item_id text,
    procurement_id text,
    pncp_procurement_id text,
    item_number integer,
    result_sequence integer NOT NULL,
    supplier_identifier text,
    supplier_name text,
    supplier_size_id integer,
    supplier_size_name text,
    legal_nature_id text,
    legal_nature_name text,
    result_date date NOT NULL,
    inclusion_at timestamptz,
    update_at timestamptz,
    cancellation_at timestamptz,
    cancellation_reason text,
    homologated_quantity numeric,
    homologated_unit_value numeric,
    homologated_total_value numeric,
    source_name text NOT NULL,
    source_payload jsonb NOT NULL,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS evt007_results_case_supplier_idx
    ON gsb.evt007_results(case_id, supplier_identifier);
CREATE INDEX IF NOT EXISTS evt007_results_result_date_idx
    ON gsb.evt007_results(result_date);
CREATE INDEX IF NOT EXISTS evt007_results_inclusion_at_idx
    ON gsb.evt007_results(inclusion_at);

CREATE TABLE IF NOT EXISTS gsb.evt007_rule_decisions (
    decision_key text PRIMARY KEY,
    scope_key text NOT NULL,
    case_id text NOT NULL,
    supplier_identifier text NOT NULL,
    rule_version text NOT NULL,
    market_state text NOT NULL,
    business_state text NOT NULL,
    route text,
    considered_items integer NOT NULL,
    qualifying_value numeric,
    reasons jsonb NOT NULL,
    decided_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gsb.evt007_opportunities (
    opportunity_id text PRIMARY KEY,
    scope_key text NOT NULL,
    case_id text NOT NULL,
    supplier_identifier text NOT NULL,
    supplier_name text NOT NULL,
    route text NOT NULL,
    qualifying_value numeric NOT NULL,
    result_date date NOT NULL,
    status text NOT NULL DEFAULT 'NOVA',
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, supplier_identifier, result_date, scope_key)
);
