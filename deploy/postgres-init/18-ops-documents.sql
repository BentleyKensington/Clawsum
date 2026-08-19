-- Document / call transcript catalog for Arcade ETL recall.
-- Apply: psql -U clawsum -d clawsum -f postgres-init/18-ops-documents.sql
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  title TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'upload',
  -- gmail | call | chatgpt | upload | scrape | other
  source_ref TEXT,
  media_id UUID REFERENCES ops.media_objects(id) ON DELETE SET NULL,
  uri TEXT,
  content_type TEXT,
  sha256 TEXT,
  summary TEXT,
  person_ids UUID[] DEFAULT '{}',
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT documents_source_chk CHECK (
    source IN ('gmail', 'call', 'chatgpt', 'upload', 'scrape', 'other')
  )
);

CREATE INDEX IF NOT EXISTS idx_documents_source ON ops.documents (source, source_ref);
CREATE INDEX IF NOT EXISTS idx_documents_sha ON ops.documents (sha256) WHERE sha256 IS NOT NULL;

CREATE TABLE IF NOT EXISTS ops.document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  document_id UUID NOT NULL REFERENCES ops.documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  char_start INT,
  char_end INT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_doc ON ops.document_chunks (document_id);

CREATE TABLE IF NOT EXISTS ops.call_recordings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  title TEXT,
  caller_person_id UUID REFERENCES ops.people(id) ON DELETE SET NULL,
  callee_person_id UUID REFERENCES ops.people(id) ON DELETE SET NULL,
  started_at TIMESTAMPTZ,
  duration_seconds INT,
  audio_media_id UUID REFERENCES ops.media_objects(id) ON DELETE SET NULL,
  transcript_media_id UUID REFERENCES ops.media_objects(id) ON DELETE SET NULL,
  document_id UUID REFERENCES ops.documents(id) ON DELETE SET NULL,
  source TEXT NOT NULL DEFAULT 'call',
  source_ref TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_call_recordings_started ON ops.call_recordings (started_at DESC NULLS LAST);

COMMENT ON TABLE ops.documents IS 'Textual documents mirrored to ArcadeDB Document/SourceChunk for graph recall';
COMMENT ON TABLE ops.call_recordings IS 'Phone call audio (.wav) + transcript in MinIO; graph via documents ETL';
