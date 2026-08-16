-- Migração 005: colunas completas do PNCP (resultado + item + contratação)
-- Objetivo (Vazquez): trazer TODOS os campos para coluna, analisar,
-- e decidir o que é MONITOR (operacional) e o que é ESTATÍSTICA.
-- O source_payload (JSONB) continua guardando o registro cru integral.

-- ===== BLOCO RESULTADO (homologação) =====
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS estimated_total_value    numeric;   -- valor estimado (p/ gatilho 85%)
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS channel                  text;      -- VF / VM (canal)
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS discount_percent         numeric;   -- percentualDesconto
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS srp_classification_order integer;   -- ordemClassificacaoSrp (ata vs contrato)
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS subcontracting_indicator boolean;   -- indicadorSubcontratacao
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS meepp_benefit            text;      -- aplicacaoBeneficioMeEpp
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS supplier_locality        text;      -- localidadeFornecedor
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS country_code             text;      -- codigoPais
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS person_type              text;      -- tipoPessoa
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS item_result_status_id    text;      -- situacaoCompraItemResultadoId
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS item_result_status_name  text;      -- situacaoCompraItemResultadoNome
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS remaining_reserve        text;      -- reservaRemanescente (objeto {codigo,nome})

-- ===== BLOCO ITEM (o objeto) =====
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS material_or_service      text;      -- materialOuServico (M/S)
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS material_or_service_name text;      -- materialOuServicoNome
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS item_description         text;      -- descricao (objeto do item)
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS complementary_info       text;      -- informacaoComplementar
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS catalog_code             text;      -- catalogoCodigoItem
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS catalog_category         text;      -- categoriaItemCatalogo
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS item_category_id         text;      -- itemCategoriaId
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS item_category_name       text;      -- itemCategoriaNome
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS ncm_code                 text;      -- ncmNbsCodigo
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS judgment_criterion       text;      -- criterioJulgamentoNome
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS estimated_unit_value     numeric;   -- valorUnitarioEstimado
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS item_estimated_total     numeric;   -- valorTotal (estimado do item)
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS measure_unit             text;      -- unidadeMedida
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS secret_budget            boolean;   -- orcamentoSigiloso
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS benefit_type             text;      -- tipoBeneficioNome
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS item_situation           text;      -- situacaoCompraItemNome

-- ===== BLOCO CONTRATAÇÃO (descoberta) =====
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS purchase_object          text;      -- objetoCompra
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS modality_name            text;      -- modalidadeNome
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS modality_id              text;      -- modalidadeId
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS is_srp                   boolean;   -- srp (registro de preço?)
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS org_uf                   text;      -- unidadeOrgaoUfSigla
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS org_municipality         text;      -- unidadeOrgaoMunicipioNome
ALTER TABLE gsb.evt007_results ADD COLUMN IF NOT EXISTS instrument_type          text;      -- tipoInstrumentoConvocatorioNome

-- índice para as análises por canal/valor
CREATE INDEX IF NOT EXISTS idx_evt007_channel ON gsb.evt007_results(channel);
CREATE INDEX IF NOT EXISTS idx_evt007_estimated ON gsb.evt007_results(estimated_total_value);
