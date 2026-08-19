CREATE TABLE IF NOT EXISTS ops.content_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,
  pack_id UUID REFERENCES ops.content_packs(id) ON DELETE SET NULL,
  kind TEXT NOT NULL,
  path TEXT,
  uri TEXT,
  media_object_id UUID,
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
  approval_id UUID,
  posted_ref TEXT,
  error TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT social_queue_status_chk CHECK (
    status IN ('draft', 'pending_approval', 'approved', 'scheduled', 'posting', 'posted', 'failed', 'cancelled')
  )
);
CREATE INDEX IF NOT EXISTS idx_social_queue_status ON ops.social_queue (status, scheduled_for);
