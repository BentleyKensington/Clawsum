-- Jarvis process gate + audit log (plan-first execution).
-- Apply: psql -U clawsum -d clawsum -f postgres-init/16-jarvis-processes.sql
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.jarvis_processes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_key TEXT,
  title TEXT NOT NULL,
  intent TEXT,
  plan_md TEXT,
  status TEXT NOT NULL DEFAULT 'proposed',
  -- proposed | confirmed | running | executed | failed | cancelled | rejected
  mode TEXT NOT NULL DEFAULT 'plan_gate',
  -- plan_gate | preapproved_fast
  skill_id TEXT,
  agent_id TEXT,
  risk_tier INT NOT NULL DEFAULT 1,
  result_md TEXT,
  error_text TEXT,
  approved_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT jarvis_processes_status_chk CHECK (
    status IN (
      'proposed', 'confirmed', 'running', 'executed', 'failed', 'cancelled', 'rejected'
    )
  ),
  CONSTRAINT jarvis_processes_mode_chk CHECK (
    mode IN ('plan_gate', 'preapproved_fast', 'boss_ordered', 'batch_gate')
  )
);

CREATE INDEX IF NOT EXISTS idx_jarvis_processes_created
  ON ops.jarvis_processes (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jarvis_processes_status
  ON ops.jarvis_processes (status, created_at DESC);

CREATE TABLE IF NOT EXISTS ops.jarvis_preapproved (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  skill_id TEXT NOT NULL,
  agent_id TEXT,
  title TEXT NOT NULL,
  match_patterns TEXT[] NOT NULL DEFAULT '{}',
  max_tier INT NOT NULL DEFAULT 1,
  enabled BOOLEAN NOT NULL DEFAULT true
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_jarvis_preapproved_skill_agent
  ON ops.jarvis_preapproved (skill_id, COALESCE(agent_id, ''));

-- Seed safe fast-path skills (read / summarize / nudge — never Tier 2+)
INSERT INTO ops.jarvis_preapproved (skill_id, agent_id, title, match_patterns, max_tier)
SELECT * FROM (VALUES
  ('ceo-daily-brief', 'hermes', 'CEO / session brief (read)', ARRAY['brief me','startup brief','ceo brief','session brief']::text[], 0),
  ('gmail-inbox-review', 'hermes', 'Inbox review (summarize)', ARRAY['inbox triage','needs boss','email review']::text[], 1),
  ('research-brief', 'hermes', 'Research brief (read)', ARRAY['research','summarize research']::text[], 0),
  ('grafana-health', 'admin', 'Grafana health (read)', ARRAY['grafana','monitoring health']::text[], 0),
  ('hermes-proactive-drive', 'hermes', 'Drive questions (no exec)', ARRAY['what next','what is on fire','whats on fire']::text[], 1)
) AS v(skill_id, agent_id, title, match_patterns, max_tier)
WHERE NOT EXISTS (
  SELECT 1 FROM ops.jarvis_preapproved p WHERE p.skill_id = v.skill_id
);
