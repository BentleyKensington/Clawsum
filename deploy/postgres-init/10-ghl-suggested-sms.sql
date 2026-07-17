-- Add suggested_sms to strategic audit tables (idempotent)
DO $$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['crm'] LOOP
    EXECUTE format(
      'ALTER TABLE %I.reengage_leads ADD COLUMN IF NOT EXISTS suggested_sms text',
      s
    );
    EXECUTE format(
      'ALTER TABLE %I.conversation_reviews ADD COLUMN IF NOT EXISTS suggested_sms text',
      s
    );
  END LOOP;
END $$;
