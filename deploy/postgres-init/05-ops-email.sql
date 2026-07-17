-- Admin Gmail archive (ops schema in clawsum DB)
\c clawsum

CREATE TABLE IF NOT EXISTS ops.email_sync_state (
  id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  last_history_id TEXT,
  last_sync_at TIMESTAMPTZ,
  backfill_completed BOOLEAN NOT NULL DEFAULT FALSE,
  messages_total INT NOT NULL DEFAULT 0
);

INSERT INTO ops.email_sync_state (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS ops.emails (
  id BIGSERIAL PRIMARY KEY,
  gmail_id TEXT NOT NULL UNIQUE,
  thread_id TEXT,
  from_addr TEXT,
  to_addrs TEXT,
  cc_addrs TEXT,
  subject TEXT,
  snippet TEXT,
  body_text TEXT,
  labels TEXT,
  is_inbox BOOLEAN NOT NULL DEFAULT TRUE,
  is_sent BOOLEAN NOT NULL DEFAULT FALSE,
  received_at TIMESTAMPTZ,
  synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processing_status TEXT NOT NULL DEFAULT 'pending',
  -- pending | triaged | archived | action_required | linked_task
  triage_notes TEXT,
  paperclip_issue_id TEXT,
  assigned_agent TEXT,
  domain_guess TEXT,
  raw_headers JSONB,
  CONSTRAINT emails_status_check CHECK (
    processing_status IN (
      'pending', 'triaged', 'archived', 'action_required', 'linked_task', 'ignored'
    )
  )
);

CREATE INDEX IF NOT EXISTS idx_emails_received_at ON ops.emails (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_status ON ops.emails (processing_status);
CREATE INDEX IF NOT EXISTS idx_emails_thread ON ops.emails (thread_id);

COMMENT ON TABLE ops.emails IS 'Archived Gmail for admin agent; forward external mail to GMAIL_ADMIN_ADDRESS';
COMMENT ON COLUMN ops.emails.processing_status IS 'Admin/bot triage state; link to Paperclip via paperclip_issue_id';
