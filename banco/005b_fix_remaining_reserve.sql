-- Patch: reservaRemanescente vem como objeto {codigo,nome}, não boolean.
-- Se a coluna já existe como boolean, converte para text.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema='gsb' AND table_name='evt007_results'
             AND column_name='remaining_reserve' AND data_type='boolean') THEN
    ALTER TABLE gsb.evt007_results ALTER COLUMN remaining_reserve TYPE text
      USING remaining_reserve::text;
  END IF;
END $$;
