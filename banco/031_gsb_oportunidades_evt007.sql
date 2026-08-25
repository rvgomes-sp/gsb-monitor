-- 031 — Ouro EVT-007 (schema gsb). Grão = 1 vencedor x 1 lote = 1 contrato = 1 garantia.
-- Alimentada por coletor/esteira_evt007.py. Ver governanca/DOUTRINA_ESTEIRA_BIBLIOTECA.md.

create table if not exists gsb.oportunidades_evt007 (
  id                     bigserial primary key,
  safra                  date not null,          -- dia da coleta (fonte temporal)
  numero_controle_pncp   text,
  id_biblioteca          text,
  codigo_objeto          text, grupo_objeto text, familia text,
  garantia_codigo        text, garantia_status text,
  -- comprador
  orgao                  text, orgao_cnpj text, uf text, municipio text,
  codigo_ibge            text, esfera text, poder text,
  modalidade_id          int, modalidade text, objeto text, objeto_curto text,
  -- vencedor (1 linha = 1 vencedor x 1 lote)
  numero_item            int,
  vencedor               text, vencedor_cnpj text, porte text, natureza_juridica text,
  -- valores
  valor_estimado_total   numeric, valor_homologado_total numeric,
  valor_homologado_item  numeric, quantidade_homologada numeric,
  pct_homologado_estimado numeric, garantia_reforcada boolean,   -- regra 85% (só O)
  -- frescor
  data_resultado         date, data_inclusao timestamptz,
  delta_calendar_days    int, delta_business_days int, frescor text,
  -- fonte/safra
  fonte_plataforma       text, link_origem text,
  completo               boolean,                -- true = vencedor + data_resultado (sobe ao monitor)
  created_at             timestamptz default now()
);
create index if not exists ix_op_safra on gsb.oportunidades_evt007 (safra);
create index if not exists ix_op_grupo on gsb.oportunidades_evt007 (grupo_objeto);
create index if not exists ix_op_controle on gsb.oportunidades_evt007 (numero_controle_pncp);
