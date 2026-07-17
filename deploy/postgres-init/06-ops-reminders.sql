-- Boss reminders: daily nudge until completed or snoozed
\c clawsum

CREATE TABLE IF NOT EXISTS ops.reminders (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  due_date DATE,
  remind_daily BOOLEAN NOT NULL DEFAULT TRUE,
  snoozed_until DATE,
  completed_at TIMESTAMPTZ,
  priority TEXT NOT NULL DEFAULT 'medium',
  source TEXT NOT NULL DEFAULT 'manual',
  source_ref TEXT,
  assigned_agent TEXT,
  paperclip_issue_id TEXT,
  gmail_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT reminders_priority_check CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  CONSTRAINT reminders_source_check CHECK (
    source IN ('manual', 'gmail', 'paperclip', 'telegram', 'email')
  )
);

CREATE INDEX IF NOT EXISTS idx_reminders_active ON ops.reminders (completed_at)
  WHERE completed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_reminders_due ON ops.reminders (due_date)
  WHERE completed_at IS NULL;

COMMENT ON TABLE ops.reminders IS 'Boss task reminders; daily Telegram until done or snoozed';
COMMENT ON COLUMN ops.reminders.snoozed_until IS 'No daily reminder until this date (inclusive hide through date)';
