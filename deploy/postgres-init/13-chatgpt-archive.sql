-- ChatGPT history archive (governed RAG) — do NOT dump into Hermes memory wholesale.
-- Apply: psql -U clawsum -d clawsum -f postgres-init/13-chatgpt-archive.sql
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.chatgpt_imports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_label TEXT DEFAULT 'gerald',
  source_account TEXT,
  original_filename TEXT,
  raw_archive_uri TEXT,
  import_status TEXT DEFAULT 'uploaded',
  conversation_count INT DEFAULT 0,
  notes TEXT,
  imported_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT chatgpt_imports_status_chk CHECK (
    import_status IN ('uploaded', 'parsing', 'parsed', 'classified', 'linked', 'error')
  )
);

CREATE TABLE IF NOT EXISTS ops.conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  import_id UUID REFERENCES ops.chatgpt_imports(id) ON DELETE CASCADE,
  source_conversation_id TEXT,
  title TEXT,
  created_at_source TIMESTAMPTZ,
  updated_at_source TIMESTAMPTZ,
  primary_business_id UUID REFERENCES ops.businesses(id),
  scope TEXT DEFAULT 'unknown',
  -- personal | business | mixed | unknown
  work_status TEXT DEFAULT 'other',
  -- pending | in_progress | completed | blocked | abandoned | other
  intent_summary TEXT,
  summary TEXT,
  topics TEXT[] DEFAULT '{}',
  sensitivity_level TEXT DEFAULT 'unknown',
  paperclip_issue_id TEXT,
  paperclip_issue_identifier TEXT,
  link_confidence NUMERIC,
  clarification_questions TEXT[] DEFAULT '{}',
  proactive_flags TEXT[] DEFAULT '{}',
  approved_for_hermes BOOLEAN DEFAULT false,
  approved_for_agents BOOLEAN DEFAULT false,
  raw_json_uri TEXT,
  message_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT conversations_scope_chk CHECK (
    scope IN ('personal', 'business', 'mixed', 'unknown')
  ),
  CONSTRAINT conversations_work_status_chk CHECK (
    work_status IN ('pending', 'in_progress', 'completed', 'blocked', 'abandoned', 'other')
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_source
  ON ops.conversations (import_id, source_conversation_id);

CREATE INDEX IF NOT EXISTS idx_conversations_scope ON ops.conversations (scope);
CREATE INDEX IF NOT EXISTS idx_conversations_work_status ON ops.conversations (work_status);
CREATE INDEX IF NOT EXISTS idx_conversations_business ON ops.conversations (primary_business_id);

CREATE TABLE IF NOT EXISTS ops.messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES ops.conversations(id) ON DELETE CASCADE,
  role TEXT,
  content TEXT,
  created_at_source TIMESTAMPTZ,
  message_order INT,
  contains_sensitive BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON ops.messages (conversation_id);

CREATE TABLE IF NOT EXISTS ops.conversation_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES ops.conversations(id) ON DELETE CASCADE,
  message_id UUID REFERENCES ops.messages(id) ON DELETE SET NULL,
  chunk_text TEXT NOT NULL,
  chunk_index INT,
  business_id UUID REFERENCES ops.businesses(id),
  topic TEXT,
  sensitivity_level TEXT DEFAULT 'unknown',
  approved_for_retrieval BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.extracted_facts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES ops.businesses(id),
  source_conversation_id UUID REFERENCES ops.conversations(id) ON DELETE CASCADE,
  fact_text TEXT NOT NULL,
  fact_type TEXT,
  confidence NUMERIC,
  durable BOOLEAN DEFAULT false,
  approved_for_hermes_memory BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.extracted_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES ops.businesses(id),
  source_conversation_id UUID REFERENCES ops.conversations(id) ON DELETE CASCADE,
  task_text TEXT NOT NULL,
  status TEXT DEFAULT 'proposed',
  priority TEXT,
  paperclip_task_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT extracted_tasks_status_chk CHECK (
    status IN ('proposed', 'linked', 'done', 'dismissed')
  )
);

CREATE TABLE IF NOT EXISTS ops.archive_task_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES ops.conversations(id) ON DELETE CASCADE,
  paperclip_issue_id TEXT NOT NULL,
  paperclip_identifier TEXT,
  paperclip_title TEXT,
  paperclip_status TEXT,
  match_reason TEXT,
  confidence NUMERIC,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_archive_task_links_conv ON ops.archive_task_links (conversation_id);

COMMENT ON TABLE ops.conversations IS 'ChatGPT export conversations — classified, not auto-loaded into Hermes memory';
COMMENT ON COLUMN ops.conversations.scope IS 'personal vs business-cell relevant';
COMMENT ON COLUMN ops.conversations.work_status IS 'Derived vs Paperclip / conversation cues';
