-- =============================================================================
-- Banco de LICITAÇÕES — v2: TRIAGEM (pipeline Coleta -> Supabase -> Triagem -> Monitor)
-- O monitor lê SOMENTE licitacoes.oportunidades (casos aprovados na triagem).
-- Idempotente e aditivo.
-- =============================================================================

CREATE TABLE IF NOT EXISTS licitacoes.oportunidades (
    numero_controle_pncp   text PRIMARY KEY
                           REFERENCES licitacoes.casos(numero_controle_pncp) ON DELETE CASCADE,
    -- triagem
    status_triagem         text NOT NULL DEFAULT 'PENDENTE'
                           CHECK (status_triagem IN ('PENDENTE','APROVADA','DESCARTADA','EM_ANALISE')),
    motivo_triagem         text,                    -- por que aprovou/descartou
    triado_por             text,                    -- quem decidiu (pessoa ou 'regra:<nome>')
    triado_em              timestamptz,
    -- espelho comercial (denormalizado p/ o monitor não juntar 4 tabelas)
    rota                   text,                    -- VAZQUEZ_FONSECA | VIEIRA_MENDONCA
    valor_homologado       numeric,
    fornecedor_vencedor    text,
    fornecedor_ni          text,
    orgao                  text,
    uf                     text,
    municipio              text,
    objeto                 text,
    modalidade             text,
    data_resultado         date,
    data_inclusao_pncp     timestamptz,
    familia_principal      text,                    -- família do item de maior valor
    familia_status         text,                    -- CERTA | INFERIR | MONITORAR | PENDENTE
    ratio_85_min           numeric,                 -- menor ratio entre itens de obra (se houver)
    pct_garantia           numeric DEFAULT 5.0,
    garantia_estimada      numeric,
    -- ciclo comercial (preenchido pelo monitor/CRM depois)
    status_comercial       text NOT NULL DEFAULT 'NOVA',
    atualizado_em          timestamptz NOT NULL DEFAULT now(),
    criado_em              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS oportunidades_status_idx ON licitacoes.oportunidades(status_triagem);
CREATE INDEX IF NOT EXISTS oportunidades_rota_idx ON licitacoes.oportunidades(rota);
