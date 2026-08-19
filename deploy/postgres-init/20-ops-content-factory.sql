-- Evergreen content factory: ideas → packs → assets → social queue.
-- Apply: docker exec -i clawsum-postgres-1 psql -U clawsum -d clawsum -v ON_ERROR_STOP=1 < postgres-init/20-ops-content-factory.sql
-- Do not use \c here — it hangs under `docker exec -i`.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.content_ideas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source TEXT NOT NULL DEFAULT 'boss',
  -- boss | trend | evergreen | agent
  source_ref TEXT,
  title TEXT NOT NULL,
  seed_text TEXT,
  angle TEXT,
  evergreen BOOLEAN NOT NULL DEFAULT true,
  niche TEXT,
  status TEXT NOT NULL DEFAULT 'inbox',
  -- inbox | researching | packed | producing | ready | queued | posted | skipped
  paperclip_issue_id TEXT,
  paperclip_identifier TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT content_ideas_source_chk CHECK (
    source IN ('boss', 'trend', 'evergreen', 'agent')
  ),
  CONSTRAINT content_ideas_status_chk CHECK (
    status IN ('inbox', 'researching', 'packed', 'producing', 'ready', 'queued', 'posted', 'skipped')
  )
);

CREATE INDEX IF NOT EXISTS idx_content_ideas_status ON ops.content_ideas (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_ideas_evergreen ON ops.content_ideas (evergreen, status);

CREATE TABLE IF NOT EXISTS ops.content_packs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,
  topic TEXT NOT NULL,
  hook TEXT,
  flyer_copy TEXT,
  image_prompts JSONB NOT NULL DEFAULT '[]'::jsonb,
  social_story TEXT,
  production_script TEXT,
  seo JSONB NOT NULL DEFAULT '{}'::jsonb,
  platforms TEXT[] NOT NULL DEFAULT ARRAY['instagram', 'youtube_shorts', 'facebook'],
  pack_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_content_packs_idea ON ops.content_packs (idea_id);

CREATE TABLE IF NOT EXISTS ops.content_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,
  pack_id UUID REFERENCES ops.content_packs(id) ON DELETE SET NULL,
  kind TEXT NOT NULL,
  -- flyer | image | first_frame | thumbnail | video | script | other
  path TEXT,
  uri TEXT,
  media_object_id UUID REFERENCES ops.media_objects(id) ON DELETE SET NULL,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT content_assets_kind_chk CHECK (
    kind IN ('flyer', 'image', 'first_frame', 'thumbnail', 'video', 'script', 'other')
  )
);

CREATE INDEX IF NOT EXISTS idx_content_assets_idea ON ops.content_assets (idea_id, kind);

CREATE TABLE IF NOT EXISTS ops.social_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,
  pack_id UUID REFERENCES ops.content_packs(id) ON DELETE SET NULL,
  platform TEXT NOT NULL,
  caption TEXT,
  scheduled_for TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'draft',
  -- draft | pending_approval | approved | scheduled | posting | posted | failed | cancelled
  approval_id UUID,
  posted_ref TEXT,
  error TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT social_queue_status_chk CHECK (
    status IN ('draft', 'pending_approval', 'approved', 'scheduled', 'posting', 'posted', 'failed', 'cancelled')
  )
);

CREATE INDEX IF NOT EXISTS idx_social_queue_status ON ops.social_queue (status, scheduled_for);

COMMENT ON TABLE ops.content_ideas IS
  'Boss/Hermes/trend seeds for the daily evergreen content factory';
COMMENT ON TABLE ops.content_packs IS
  'Topic, flyer, image prompts, social story, production script';
COMMENT ON TABLE ops.social_queue IS
  'Schedule or immediate post — Tier 2 until ops.approvals approved';
