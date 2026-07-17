-- Schemas in default 'clawsum' database (non-RE/GHL domains)
\c clawsum

CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS coding;
CREATE SCHEMA IF NOT EXISTS data;
CREATE SCHEMA IF NOT EXISTS comms;
CREATE SCHEMA IF NOT EXISTS research;
CREATE SCHEMA IF NOT EXISTS planning;

COMMENT ON SCHEMA ops IS 'admin agent — orchestration metadata, audit';
