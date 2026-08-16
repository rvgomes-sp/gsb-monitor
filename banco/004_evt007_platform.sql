-- 004_evt007_platform.sql
-- Decisão C (Vazquez, negócio): coletar TODAS as plataformas de origem,
-- marcar a plataforma (usuarioNome do PNCP) e o estado do delta.
-- Compras.gov = delta verificado manualmente; demais = a caracterizar pelo próprio dado.

ALTER TABLE gsb.evt007_results
    ADD COLUMN IF NOT EXISTS platform text,
    ADD COLUMN IF NOT EXISTS platform_delta_status text
        NOT NULL DEFAULT 'A_CARACTERIZAR';

-- índice para o comercial atacar primeiro o que está verificado,
-- e para medir o delta por plataforma ao longo do tempo.
CREATE INDEX IF NOT EXISTS evt007_results_platform_idx
    ON gsb.evt007_results(platform, platform_delta_status);

COMMENT ON COLUMN gsb.evt007_results.platform IS
    'Plataforma de origem que transmitiu ao PNCP (campo usuarioNome da Consulta). Ex.: Compras.gov.br, Pública Tecnologia, LicitaCon TCE-RS.';
COMMENT ON COLUMN gsb.evt007_results.platform_delta_status IS
    'VERIFICADO = delta homologação↔dataResultado conferido (Compras.gov). A_CARACTERIZAR = demais plataformas, delta a medir pelo dado.';
