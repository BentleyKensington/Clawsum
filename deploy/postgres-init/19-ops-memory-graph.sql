-- Clawsum memory graph (Phase 1) — fact-centric SoR in Postgres; Arcade mirrors relationships.
-- Apply: psql -U clawsum -d clawsum -f postgres-init/19-ops-memory-graph.sql
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

-- Typed durable / working facts (not chat blobs)
CREATE TABLE IF NOT EXISTS ops.memory_facts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fact_key TEXT NOT NULL,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object TEXT NOT NULL,
  fact_type TEXT NOT NULL DEFAULT 'observation',
  -- ownership | preference | goal | relationship | task | problem | project | attribute | observation
  importance TEXT NOT NULL DEFAULT 'medium',
  -- critical | high | medium | low | temporary
  confidence TEXT NOT NULL DEFAULT 'inferred',
  -- observed | confirmed | user_stated | inferred | guessed
  confidence_score NUMERIC(4,3),
  status TEXT NOT NULL DEFAULT 'active',
  -- active | historical | merged | deleted
  scope TEXT NOT NULL DEFAULT 'business',
  -- personal | business | mixed | unknown
  source_host TEXT NOT NULL DEFAULT 'vps',
  -- vps | local
  source_kind TEXT NOT NULL DEFAULT 'manual',
  -- chat | email | manual | chatgpt | dream | session_brief
  source_ref TEXT,
  source_agent TEXT,
  evidence TEXT,
  valid_from TIMESTAMPTZ DEFAULT now(),
  valid_to TIMESTAMPTZ,
  last_referenced_at TIMESTAMPTZ,
  superseded_by UUID REFERENCES ops.memory_facts(id) ON DELETE SET NULL,
  arcade_synced_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT memory_facts_importance_chk CHECK (
    importance IN ('critical', 'high', 'medium', 'low', 'temporary')
  ),
  CONSTRAINT memory_facts_confidence_chk CHECK (
    confidence IN ('observed', 'confirmed', 'user_stated', 'inferred', 'guessed')
  ),
  CONSTRAINT memory_facts_status_chk CHECK (
    status IN ('active', 'historical', 'merged', 'deleted')
  ),
  CONSTRAINT memory_facts_scope_chk CHECK (
    scope IN ('personal', 'business', 'mixed', 'unknown')
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_facts_fact_key
  ON ops.memory_facts (fact_key);

CREATE INDEX IF NOT EXISTS idx_memory_facts_status_importance
  ON ops.memory_facts (status, importance);

CREATE INDEX IF NOT EXISTS idx_memory_facts_subject
  ON ops.memory_facts (subject);

CREATE INDEX IF NOT EXISTS idx_memory_facts_predicate
  ON ops.memory_facts (predicate);

CREATE INDEX IF NOT EXISTS idx_memory_facts_updated
  ON ops.memory_facts (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_facts_source_host
  ON ops.memory_facts (source_host, updated_at DESC);

COMMENT ON TABLE ops.memory_facts IS
  'Phase-1 fact-centric memory SoR; Arcade mirrors Entity/Rel graph. No secrets.';

-- Episodic experiences (not everything becomes semantic)
CREATE TABLE IF NOT EXISTS ops.memory_episodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  summary TEXT,
  outcome TEXT,
  result_state TEXT,
  -- open | waiting | done | abandoned
  importance TEXT NOT NULL DEFAULT 'medium',
  scope TEXT NOT NULL DEFAULT 'business',
  source_host TEXT NOT NULL DEFAULT 'vps',
  source_kind TEXT NOT NULL DEFAULT 'manual',
  source_ref TEXT,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  fact_ids UUID[] NOT NULL DEFAULT '{}',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT memory_episodes_importance_chk CHECK (
    importance IN ('critical', 'high', 'medium', 'low', 'temporary')
  ),
  CONSTRAINT memory_episodes_scope_chk CHECK (
    scope IN ('personal', 'business', 'mixed', 'unknown')
  )
);

CREATE INDEX IF NOT EXISTS idx_memory_episodes_updated
  ON ops.memory_episodes (updated_at DESC);

COMMENT ON TABLE ops.memory_episodes IS
  'Episodic memory — conversations/outcomes that stay as experiences.';

-- Dream / consolidation run log (workers land in Phase 2+)
CREATE TABLE IF NOT EXISTS ops.memory_dream_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stage TEXT NOT NULL,
  -- immediate | hourly | nightly | weekly | monthly
  source_host TEXT NOT NULL DEFAULT 'vps',
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  ok BOOLEAN,
  stats JSONB NOT NULL DEFAULT '{}'::jsonb,
  notes TEXT,
  CONSTRAINT memory_dream_runs_stage_chk CHECK (
    stage IN ('immediate', 'hourly', 'nightly', 'weekly', 'monthly')
  )
);

CREATE INDEX IF NOT EXISTS idx_memory_dream_runs_started
  ON ops.memory_dream_runs (started_at DESC);

COMMENT ON TABLE ops.memory_dream_runs IS
  'Consolidation job history; Phase 1 creates table only.';
