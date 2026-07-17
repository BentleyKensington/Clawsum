-- Generic GHL agent schema (template default: one location, schema crm)
-- Multi-account instance overlay: see config/ghl-accounts.instance.rei.example.json + 07b script

CREATE SCHEMA IF NOT EXISTS crm;
COMMENT ON SCHEMA crm IS 'ghl agent only — single GHL location per instance';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ghl_crm') THEN
    CREATE ROLE ghl_crm LOGIN PASSWORD 'ghl_crm_change_me';
  END IF;
END $$;

REVOKE ALL ON SCHEMA public FROM ghl_crm;
GRANT USAGE ON SCHEMA crm TO ghl_crm;
GRANT CREATE ON SCHEMA crm TO ghl_crm;
GRANT ALL ON ALL TABLES IN SCHEMA crm TO ghl_crm;
GRANT ALL ON ALL SEQUENCES IN SCHEMA crm TO ghl_crm;
ALTER DEFAULT PRIVILEGES IN SCHEMA crm GRANT ALL ON TABLES TO ghl_crm;
ALTER DEFAULT PRIVILEGES IN SCHEMA crm GRANT ALL ON SEQUENCES TO ghl_crm;
ALTER ROLE ghl_crm SET search_path TO crm;
