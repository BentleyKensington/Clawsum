-- Session Startup Briefs archive (Hermes BOOT.md first messages).
-- Apply: psql -U clawsum -d clawsum -f postgres-init/15-session-briefs.sql
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.session_briefs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_key TEXT,
  greeting TEXT,
  body_md TEXT NOT NULL,
  source TEXT DEFAULT 'hermes',
  -- hermes | manual | import
  file_uri TEXT,
  CONSTRAINT session_briefs_source_chk CHECK (
    source IN ('hermes', 'manual', 'import')
  )
);

CREATE INDEX IF NOT EXISTS idx_session_briefs_created
  ON ops.session_briefs (created_at DESC);
