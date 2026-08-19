-- Media objects (MinIO) + email attachment metadata + contact helpers.
-- Apply: psql -U clawsum -d clawsum -f postgres-init/17-ops-media-graph.sql
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

-- Gmail / sync attachment metadata on the email row (quick list)
ALTER TABLE ops.emails
  ADD COLUMN IF NOT EXISTS attachments JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN ops.emails.attachments IS
  'Array of {filename,content_type,size,bucket,key,uri,sha256,kind} for MinIO-archived parts';

-- Durable media catalog (photos, videos, docs, wav, transcripts)
CREATE TABLE IF NOT EXISTS ops.media_objects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  bucket TEXT NOT NULL,
  object_key TEXT NOT NULL,
  uri TEXT NOT NULL,
  content_type TEXT,
  size_bytes BIGINT,
  sha256 TEXT,
  source TEXT NOT NULL DEFAULT 'upload',
  -- gmail | call | upload | chatgpt | scrape | other
  source_ref TEXT,
  email_id BIGINT REFERENCES ops.emails(id) ON DELETE SET NULL,
  person_id UUID REFERENCES ops.people(id) ON DELETE SET NULL,
  place_id UUID REFERENCES ops.places(id) ON DELETE SET NULL,
  kind TEXT NOT NULL DEFAULT 'attachment',
  -- attachment | photo | video | document | audio | transcript | other
  filename TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT media_objects_source_chk CHECK (
    source IN ('gmail', 'call', 'upload', 'chatgpt', 'scrape', 'other')
  ),
  CONSTRAINT media_objects_kind_chk CHECK (
    kind IN ('attachment', 'photo', 'video', 'document', 'audio', 'transcript', 'other')
  ),
  CONSTRAINT media_objects_bucket_key_uq UNIQUE (bucket, object_key)
);

CREATE INDEX IF NOT EXISTS idx_media_objects_source
  ON ops.media_objects (source, source_ref);
CREATE INDEX IF NOT EXISTS idx_media_objects_email
  ON ops.media_objects (email_id)
  WHERE email_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_objects_person
  ON ops.media_objects (person_id)
  WHERE person_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_objects_sha
  ON ops.media_objects (sha256)
  WHERE sha256 IS NOT NULL;

-- Faster contact match by phone / secondary email
CREATE INDEX IF NOT EXISTS idx_people_emails_gin
  ON ops.people USING GIN (emails);
CREATE INDEX IF NOT EXISTS idx_people_phones_gin
  ON ops.people USING GIN (phones);

COMMENT ON TABLE ops.media_objects IS
  'MinIO object catalog; blobs live in MinIO, recall metadata + person links here and in ArcadeDB';
