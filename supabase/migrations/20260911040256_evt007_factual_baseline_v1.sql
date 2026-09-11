-- 003-S / 02-R / Etapa 2. New physical factual baseline only.
-- Target: wpsvmrmuxdvajjumdjqp. No import from older projects.
CREATE SCHEMA IF NOT EXISTS gsb;

CREATE TABLE gsb.evt007_collection_runs (
  run_id text PRIMARY KEY,
  result_date date NOT NULL,
  source_name text NOT NULL,
  source_endpoint text NOT NULL,
  status text NOT NULL CHECK (status IN ('RUNNING','FACTUAL_PRESERVED','COMPLETE','COMPLETE_EMPTY','FAILED')),
  page_size integer NOT NULL CHECK (page_size BETWEEN 1 AND 500),
  expected_pages integer CHECK (expected_pages >= 0),
  expected_records bigint CHECK (expected_records >= 0),
  collected_pages integer NOT NULL DEFAULT 0 CHECK (collected_pages >= 0),
  collected_records bigint NOT NULL DEFAULT 0 CHECK (collected_records >= 0),
  mapped_records bigint NOT NULL DEFAULT 0 CHECK (mapped_records >= 0),
  metrics jsonb,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  error_message text
);

CREATE TABLE gsb.evt007_raw_pages (
  run_id text NOT NULL REFERENCES gsb.evt007_collection_runs(run_id),
  page_number integer NOT NULL CHECK (page_number > 0),
  request_url text NOT NULL,
  http_status integer NOT NULL CHECK (http_status BETWEEN 100 AND 599),
  payload_sha256 text NOT NULL CHECK (length(payload_sha256)=64),
  payload_raw bytea NOT NULL,
  payload jsonb NOT NULL,
  received_at timestamptz NOT NULL,
  PRIMARY KEY (run_id,page_number)
);

CREATE TABLE gsb.evt007_results (
  result_key text PRIMARY KEY,
  case_id text NOT NULL,
  item_number integer NOT NULL CHECK (item_number > 0),
  result_sequence integer NOT NULL,
  supplier_identifier text NOT NULL,
  supplier_name text,
  supplier_size_id integer,
  supplier_size_name text,
  legal_nature_id text,
  legal_nature_name text,
  result_date date NOT NULL,
  inclusion_at timestamptz,
  update_at timestamptz,
  cancellation_at timestamptz,
  homologated_quantity numeric,
  homologated_unit_value numeric,
  homologated_total_value numeric,
  platform text,
  platform_delta_status text,
  source_name text NOT NULL,
  source_payload jsonb NOT NULL,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX evt007_results_date_idx ON gsb.evt007_results(result_date);
CREATE INDEX evt007_results_item_idx ON gsb.evt007_results(case_id,item_number);

ALTER TABLE gsb.evt007_collection_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsb.evt007_raw_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsb.evt007_results ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON gsb.evt007_collection_runs, gsb.evt007_raw_pages, gsb.evt007_results FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA gsb TO service_role;
GRANT SELECT, INSERT ON gsb.evt007_raw_pages, gsb.evt007_results TO service_role;
GRANT SELECT, INSERT, UPDATE ON gsb.evt007_collection_runs TO service_role;
