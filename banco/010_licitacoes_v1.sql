-- =============================================================================
-- GSB Monitor / Observatório SG — Banco de LICITAÇÕES (EVT-007) — schema v1
-- Fonte única: PNCP API v1 (Consulta + Integração), Manual v2.5.
-- Banco VIVO e PROBATÓRIO: guarda o fato (todas as linhas de resultado =
-- vencedor + reserva/remanescente), a evidência bruta e o log de eventos.
-- Idempotente (CREATE IF NOT EXISTS). Projeto dedicado observatorio-sg.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS licitacoes;

-- ---------------------------------------------------------------------------
-- coletas — uma execução do motor (run). Retomável, honesta (COMPLETE/PARTIAL).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licitacoes.coletas (
    run_id              uuid PRIMARY KEY,
    data_alvo           date NOT NULL,                 -- dia D coletado
    rede_por            text NOT NULL DEFAULT 'inclusao_resultado_10_19',
    modalidades         integer[] NOT NULL,            -- ex: {4,5,6,7}
    piso_valor          numeric NOT NULL,              -- ex: 10000000
    status              text NOT NULL DEFAULT 'RODANDO' -- RODANDO|COMPLETE|PARTIAL|ERRO
                        CHECK (status IN ('RODANDO','COMPLETE','PARTIAL','ERRO')),
    paginas_lidas       integer NOT NULL DEFAULT 0,
    paginas_puladas     integer NOT NULL DEFAULT 0,    -- páginas instáveis do PNCP
    casos_descobertos   integer NOT NULL DEFAULT 0,
    casos_qualificados  integer NOT NULL DEFAULT 0,
    resultados_gravados integer NOT NULL DEFAULT 0,
    started_at          timestamptz NOT NULL DEFAULT now(),
    finished_at         timestamptz,
    erro                text
);
CREATE INDEX IF NOT EXISTS coletas_data_idx ON licitacoes.coletas(data_alvo);

-- ---------------------------------------------------------------------------
-- casos — a contratação (10.5 / descoberta atualizacao). Chave: numeroControlePNCP.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licitacoes.casos (
    numero_controle_pncp    text PRIMARY KEY,
    cnpj_orgao              text NOT NULL,
    ano                     integer NOT NULL,
    sequencial              integer NOT NULL,
    numero_compra           text,
    modalidade_id           integer,
    modalidade_nome         text,
    modo_disputa_id         integer,
    modo_disputa_nome       text,
    situacao_compra_id      integer,
    situacao_compra_nome    text,
    objeto_compra           text,
    informacao_complementar text,
    srp                     boolean,
    valor_total_estimado    numeric,
    valor_total_homologado  numeric,                   -- homologado do caso (10.5 id 20)
    orgao_razao_social      text,
    uf                      text,
    municipio               text,
    usuario_nome            text,                      -- plataforma de origem
    link_sistema_origem     text,
    data_atualizacao_global timestamptz,
    rota                    text,                      -- VAZQUEZ_FONSECA (>10MM) etc.
    run_id                  uuid REFERENCES licitacoes.coletas(run_id),
    primeira_coleta         timestamptz NOT NULL DEFAULT now(),
    ultima_coleta           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (cnpj_orgao, ano, sequencial)
);
CREATE INDEX IF NOT EXISTS casos_homologado_idx ON licitacoes.casos(valor_total_homologado);
CREATE INDEX IF NOT EXISTS casos_uf_idx ON licitacoes.casos(uf);

-- ---------------------------------------------------------------------------
-- itens — o objeto (10.13). Família classificada por CÓDIGO de catálogo.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licitacoes.itens (
    numero_controle_pncp        text NOT NULL REFERENCES licitacoes.casos(numero_controle_pncp) ON DELETE CASCADE,
    numero_item                 integer NOT NULL,
    material_ou_servico         text,                  -- M | S
    descricao                   text,
    quantidade                  numeric,
    unidade_medida              text,
    valor_unitario_estimado     numeric,
    valor_total_estimado        numeric,               -- base do gatilho 85% (obras)
    criterio_julgamento_nome    text,
    tem_resultado               boolean,
    -- catálogo (opcionais no PNCP; podem vir nulos)
    catalogo_codigo_item        text,
    catalogo_id                 integer,
    catalogo_nome               text,
    categoria_item_catalogo_id  integer,
    categoria_item_catalogo_nome text,
    item_categoria_id           integer,               -- 1 imóvel/2 móvel/3 N-A (NÃO é família)
    ncm_nbs_codigo              text,
    -- classificação de família (por código, nunca palavra-chave)
    familia_codigo              text,                  -- classe/divisão CATMAT/CATSER
    familia_nome                text,
    familia_status              text                   -- CERTA|INFERIR|MONITORAR|DESCARTAR|PENDENTE
                                DEFAULT 'PENDENTE',
    PRIMARY KEY (numero_controle_pncp, numero_item)
);
CREATE INDEX IF NOT EXISTS itens_familia_status_idx ON licitacoes.itens(familia_status);
CREATE INDEX IF NOT EXISTS itens_familia_codigo_idx ON licitacoes.itens(familia_codigo);

-- ---------------------------------------------------------------------------
-- resultados — a homologação (10.17). BANCO VIVO de participantes:
-- todas as linhas por item (vencedor + reserva/remanescente).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licitacoes.resultados (
    numero_controle_pncp        text NOT NULL,
    numero_item                 integer NOT NULL,
    sequencial_resultado        integer NOT NULL,
    ni_fornecedor               text,                  -- CNPJ (pode ser alfanumérico) / CPF
    nome_fornecedor             text,
    tipo_pessoa                 text,                  -- PJ | PF | PE
    porte_id                    integer,               -- 3 = Demais (alvo)
    porte_nome                  text,
    natureza_juridica_id        integer,
    natureza_juridica_nome      text,
    codigo_pais                 text,
    quantidade_homologada       numeric,
    valor_unitario_homologado   numeric,
    valor_total_homologado_item numeric GENERATED ALWAYS AS
                                (COALESCE(quantidade_homologada,0) * COALESCE(valor_unitario_homologado,0)) STORED,
    data_resultado              date,                  -- marco (não fundir com inclusão)
    data_inclusao               timestamptz,           -- entrada no PNCP (estável)
    situacao_resultado_id       integer,               -- 1 Informado | 2 Cancelado
    situacao_resultado_nome     text,
    data_cancelamento           timestamptz,
    indicador_subcontratacao    boolean,
    ordem_classificacao_srp     integer,
    reserva_remanescente_codigo integer,               -- 1 N/A | 2 Remanescente | 3 Reserva
    reserva_remanescente_nome   text,
    papel                       text,                  -- VENCEDOR | RESERVA | REMANESCENTE
    ratio_85                    numeric,               -- só itens de obra
    run_id                      uuid REFERENCES licitacoes.coletas(run_id),
    primeira_coleta             timestamptz NOT NULL DEFAULT now(),
    ultima_coleta               timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (numero_controle_pncp, numero_item, sequencial_resultado),
    FOREIGN KEY (numero_controle_pncp, numero_item)
        REFERENCES licitacoes.itens(numero_controle_pncp, numero_item) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS resultados_fornecedor_idx ON licitacoes.resultados(ni_fornecedor);
CREATE INDEX IF NOT EXISTS resultados_data_resultado_idx ON licitacoes.resultados(data_resultado);
CREATE INDEX IF NOT EXISTS resultados_data_inclusao_idx ON licitacoes.resultados(data_inclusao);

-- ---------------------------------------------------------------------------
-- eventos — histórico da contratação (10.19). Rede de datas auditável:
-- inclusão de resultado (categoria 5, tipo 0) = EVT-007 novo no dia D.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licitacoes.eventos (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    numero_controle_pncp    text NOT NULL,
    log_data_inclusao       timestamptz NOT NULL,
    tipo_log                integer NOT NULL,          -- 0 Inclusão | 1 Retificação | 2 Exclusão
    tipo_log_nome           text,
    categoria_log           integer NOT NULL,          -- 5 = Resultado de Item
    categoria_log_nome      text,
    item_numero             integer,
    item_resultado_numero   integer,
    run_id                  uuid REFERENCES licitacoes.coletas(run_id),
    capturado_em            timestamptz NOT NULL DEFAULT now()
);
-- dedup do mesmo evento (idempotência da coleta)
CREATE UNIQUE INDEX IF NOT EXISTS eventos_natural_uk ON licitacoes.eventos(
    numero_controle_pncp, log_data_inclusao, categoria_log, tipo_log,
    COALESCE(item_numero,-1), COALESCE(item_resultado_numero,-1)
);
CREATE INDEX IF NOT EXISTS eventos_data_idx ON licitacoes.eventos(log_data_inclusao);

-- ---------------------------------------------------------------------------
-- evidencia_bruta — bytes originais de cada resposta PNCP (probatório).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licitacoes.evidencia_bruta (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        uuid REFERENCES licitacoes.coletas(run_id),
    endpoint      text NOT NULL,                       -- ex: 10.17
    url           text NOT NULL,
    http_status   integer,
    source_hash   text NOT NULL,                       -- sha256(raw)
    latencia_ms   integer,
    payload       jsonb,
    recebido_em   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS evidencia_run_idx ON licitacoes.evidencia_bruta(run_id);
