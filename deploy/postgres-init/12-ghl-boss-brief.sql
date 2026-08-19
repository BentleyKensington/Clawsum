-- Boss-facing priority explanation + contact brief (idempotent)
DO $$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['crm', 'mco_rei', 'ave_rei', 'wnn_rei', 'dispo_dudes'] LOOP
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = s) THEN
      CONTINUE;
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = s AND table_name = 'reengage_leads'
    ) THEN
      CONTINUE;
    END IF;
    EXECUTE format(
      'ALTER TABLE %I.reengage_leads ADD COLUMN IF NOT EXISTS priority_why text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.reengage_leads ADD COLUMN IF NOT EXISTS boss_brief text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.reengage_leads ADD COLUMN IF NOT EXISTS situation_kind text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.conversation_reviews ADD COLUMN IF NOT EXISTS priority_why text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.conversation_reviews ADD COLUMN IF NOT EXISTS boss_brief text',
      s
    );
  END LOOP;
END $$;
