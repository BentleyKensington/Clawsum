-- INSTANCE OVERLAY ONLY — multi-account REI schemas (not generic template default)
-- Apply when ghl-accounts.json lists mco_rei / ave_rei / wnn_rei accounts.

CREATE SCHEMA IF NOT EXISTS mco_rei;
CREATE SCHEMA IF NOT EXISTS ave_rei;
CREATE SCHEMA IF NOT EXISTS wnn_rei;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ghl_mco_rei') THEN
    CREATE ROLE ghl_mco_rei LOGIN PASSWORD 'ghl_mco_rei_change_me';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ghl_ave_rei') THEN
    CREATE ROLE ghl_ave_rei LOGIN PASSWORD 'ghl_ave_rei_change_me';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ghl_wnn_rei') THEN
    CREATE ROLE ghl_wnn_rei LOGIN PASSWORD 'ghl_wnn_rei_change_me';
  END IF;
END $$;

-- Grant per-schema isolation (see prior 07-ghl-account-schemas.sql in git history for full REVOKE/GRANT blocks)
