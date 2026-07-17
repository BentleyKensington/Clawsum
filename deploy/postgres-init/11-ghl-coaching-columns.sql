-- Coaching + specific-hook columns for strategic audit (idempotent)
DO $$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['crm'] LOOP
    EXECUTE format(
      'ALTER TABLE %I.reengage_leads ADD COLUMN IF NOT EXISTS contact_specific_hook text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.reengage_leads ADD COLUMN IF NOT EXISTS what_went_wrong text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.reengage_leads ADD COLUMN IF NOT EXISTS process_improvement text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.conversation_reviews ADD COLUMN IF NOT EXISTS contact_specific_hook text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.conversation_reviews ADD COLUMN IF NOT EXISTS what_went_wrong text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.conversation_reviews ADD COLUMN IF NOT EXISTS process_improvement text',
      s
    );
  END LOOP;
END $$;
