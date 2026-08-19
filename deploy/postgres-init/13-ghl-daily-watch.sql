-- Daily roster watch: previously reported contacts (idempotent)
DO $$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['crm', 'mco_rei', 'ave_rei', 'wnn_rei', 'dispo_dudes'] LOOP
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = s) THEN
      CONTINUE;
    END IF;
    EXECUTE format($SQL$
      CREATE TABLE IF NOT EXISTS %I.daily_watch (
        contact_id text PRIMARY KEY,
        contact_name text,
        phone text,
        first_seen_on date NOT NULL DEFAULT CURRENT_DATE,
        last_seen_on date NOT NULL DEFAULT CURRENT_DATE,
        last_status text NOT NULL DEFAULT 'open',
        last_priority text,
        last_situation text,
        last_reason text,
        report_count int NOT NULL DEFAULT 0,
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    $SQL$, s);
  END LOOP;
END $$;
