-- GHL audit tables (per account schema)
-- Run: docker exec -i clawsum-postgres-1 psql -U clawsum -d ghl -v ON_ERROR_STOP=1 < 08-ghl-audit-tables.sql

DO $$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['crm'] LOOP
    EXECUTE format($SQL$
      CREATE TABLE IF NOT EXISTS %I.audit_runs (
        id serial PRIMARY KEY,
        slug text NOT NULL,
        location_id text NOT NULL,
        started_at timestamptz NOT NULL DEFAULT now(),
        finished_at timestamptz,
        status text NOT NULL DEFAULT 'running',
        summary text,
        tool_calls int NOT NULL DEFAULT 0,
        obsidian_path text,
        raw_tools jsonb
      );

      CREATE TABLE IF NOT EXISTS %I.findings (
        id serial PRIMARY KEY,
        audit_run_id int NOT NULL REFERENCES %I.audit_runs(id) ON DELETE CASCADE,
        category text NOT NULL,
        severity text NOT NULL DEFAULT 'info',
        title text NOT NULL,
        detail text,
        recommendation text,
        ghl_entity_type text,
        ghl_entity_id text,
        metric_value numeric,
        created_at timestamptz NOT NULL DEFAULT now()
      );

      CREATE INDEX IF NOT EXISTS findings_audit_run_id ON %I.findings(audit_run_id);
      CREATE INDEX IF NOT EXISTS findings_category ON %I.findings(category);
    $SQL$, s, s, s, s, s);
  END LOOP;
END $$;
