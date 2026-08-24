-- =============================================================================
-- SIDECAR EXPERIMENTAL — Perfil Temporal de Integração EVT-007 por origem.
-- NÃO é schema canônico de produção. Guarda observações de latência
-- (delta = dataInclusao - dataResultado) por source_sender_raw (usuarioNome cru).
-- Promover para a camada factual só após estabilidade multissafra/multiplataforma.
-- Preserva SEMPRE as duas datas brutas (delta é derivado).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS gsb;

CREATE TABLE IF NOT EXISTS gsb.evt007_latency_observations (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    result_key        text NOT NULL,
    dia_coleta        date NOT NULL,
    source_sender_raw text,            -- usuarioNome cru (NÃO é "plataforma" ainda)
    source_host       text,            -- host do linkSistemaOrigem
    source_type       text,            -- PRIVATE_PLATFORM | ORG_SYSTEM | UNKNOWN (heurístico)
    org_cnpj          text,
    org_name          text,
    uf                text,
    modalidade_id     integer,
    modalidade        text,
    data_resultado    date,            -- data bruta
    data_inclusao     timestamptz,     -- data bruta
    delta_days        integer,
    delta_bucket      text,            -- D0 | D1 | D2 | D3_PLUS | ANOMALIA
    inclusion_hour    integer,
    run_id            text,
    observed_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (result_key, dia_coleta)
);
CREATE INDEX IF NOT EXISTS latency_src_idx ON gsb.evt007_latency_observations(source_sender_raw);
CREATE INDEX IF NOT EXISTS latency_dia_idx ON gsb.evt007_latency_observations(dia_coleta);
CREATE INDEX IF NOT EXISTS latency_bucket_idx ON gsb.evt007_latency_observations(delta_bucket);
