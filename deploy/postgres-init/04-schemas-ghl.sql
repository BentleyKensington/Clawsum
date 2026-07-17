\c ghl

CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS pipelines;
CREATE SCHEMA IF NOT EXISTS contacts;
CREATE SCHEMA IF NOT EXISTS campaigns;

COMMENT ON DATABASE ghl IS 'ghl agent only — CRM; crossover to RE via API/tasks not shared DB';
