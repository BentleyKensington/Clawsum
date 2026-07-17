-- Strategic audit: re-engagement leads + conversation reviews
DO $$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['crm'] LOOP
    EXECUTE format($SQL$
      CREATE TABLE IF NOT EXISTS %I.reengage_leads (
        id serial PRIMARY KEY,
        audit_run_id int REFERENCES %I.audit_runs(id) ON DELETE CASCADE,
        contact_id text NOT NULL,
        contact_name text,
        phone text,
        email text,
        date_added timestamptz,
        last_activity timestamptz,
        priority text NOT NULL DEFAULT 'medium',
        reason text NOT NULL,
        suggested_action text,
        suggested_sms text,
        contact_specific_hook text,
        what_went_wrong text,
        process_improvement text,
        pipeline_name text,
        stage_name text,
        tags text,
        created_at timestamptz NOT NULL DEFAULT now()
      );

      CREATE TABLE IF NOT EXISTS %I.conversation_reviews (
        id serial PRIMARY KEY,
        audit_run_id int REFERENCES %I.audit_runs(id) ON DELETE CASCADE,
        conversation_id text NOT NULL,
        contact_id text,
        contact_name text,
        channel text,
        last_inbound_at timestamptz,
        last_outbound_at timestamptz,
        missed_opportunity text,
        transcript_excerpt text,
        suggested_sms text,
        contact_specific_hook text,
        what_went_wrong text,
        process_improvement text,
        created_at timestamptz NOT NULL DEFAULT now()
      );

      CREATE INDEX IF NOT EXISTS reengage_audit_run ON %I.reengage_leads(audit_run_id);
      CREATE INDEX IF NOT EXISTS conv_review_audit_run ON %I.conversation_reviews(audit_run_id);
    $SQL$, s, s, s, s, s, s);
  END LOOP;
END $$;
