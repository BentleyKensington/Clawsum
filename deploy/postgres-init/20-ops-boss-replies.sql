-- Ask Boss direct replies from the cockpit.
\c clawsum
CREATE SCHEMA IF NOT EXISTS ops;
CREATE TABLE IF NOT EXISTS ops.boss_replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id TEXT,
  question TEXT NOT NULL,
  reply TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_boss_replies_created ON ops.boss_replies (created_at DESC);
COMMENT ON TABLE ops.boss_replies IS 'Boss answers to Ask Boss items from the CEO cockpit.';
