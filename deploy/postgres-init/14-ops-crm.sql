-- Clawsum CRM layer: people, places, local tasks — linked to cells, emails, reminders.
-- Apply: psql -U clawsum -d clawsum -f postgres-init/14-ops-crm.sql
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

-- ---------------------------------------------------------------------------
-- People
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ops.people (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name TEXT NOT NULL,
  sort_name TEXT,
  kind TEXT NOT NULL DEFAULT 'contact',
  -- contact | boss | teammate | vendor | client | lead | org | system
  primary_email TEXT,
  emails TEXT[] DEFAULT '{}',
  phones TEXT[] DEFAULT '{}',
  company_name TEXT,
  title_role TEXT,
  primary_business_id UUID REFERENCES ops.businesses(id) ON DELETE SET NULL,
  tags TEXT[] DEFAULT '{}',
  notes TEXT,
  ghl_contact_id TEXT,
  paperclip_user_id TEXT,
  telegram_id TEXT,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT people_kind_chk CHECK (
    kind IN ('contact', 'boss', 'teammate', 'vendor', 'client', 'lead', 'org', 'system')
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_people_primary_email_unique
  ON ops.people (lower(primary_email))
  WHERE primary_email IS NOT NULL AND primary_email <> '';

CREATE INDEX IF NOT EXISTS idx_people_business ON ops.people (primary_business_id);
CREATE INDEX IF NOT EXISTS idx_people_kind ON ops.people (kind);

-- ---------------------------------------------------------------------------
-- Places
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ops.places (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'other',
  -- office | home | property | venue | city | region | virtual | other
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  region TEXT,
  postal_code TEXT,
  country TEXT DEFAULT 'US',
  lat NUMERIC,
  lng NUMERIC,
  timezone TEXT,
  primary_business_id UUID REFERENCES ops.businesses(id) ON DELETE SET NULL,
  tags TEXT[] DEFAULT '{}',
  notes TEXT,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT places_kind_chk CHECK (
    kind IN ('office', 'home', 'property', 'venue', 'city', 'region', 'virtual', 'other')
  )
);

CREATE INDEX IF NOT EXISTS idx_places_business ON ops.places (primary_business_id);
CREATE INDEX IF NOT EXISTS idx_places_kind ON ops.places (kind);

CREATE TABLE IF NOT EXISTS ops.person_places (
  person_id UUID REFERENCES ops.people(id) ON DELETE CASCADE,
  place_id UUID REFERENCES ops.places(id) ON DELETE CASCADE,
  relation TEXT DEFAULT 'associated',
  -- associated | lives_at | works_at | owns | visits
  is_primary BOOLEAN DEFAULT false,
  PRIMARY KEY (person_id, place_id)
);

-- ---------------------------------------------------------------------------
-- Local tasks (Hermes / overwatch mirror — Paperclip remains execution truth)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ops.tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  -- pending | in_progress | blocked | completed | cancelled | deferred
  priority TEXT NOT NULL DEFAULT 'medium',
  business_id UUID REFERENCES ops.businesses(id) ON DELETE SET NULL,
  person_id UUID REFERENCES ops.people(id) ON DELETE SET NULL,
  place_id UUID REFERENCES ops.places(id) ON DELETE SET NULL,
  due_at TIMESTAMPTZ,
  source TEXT NOT NULL DEFAULT 'manual',
  -- manual | gmail | chatgpt_archive | paperclip | hermes | reminder
  source_ref TEXT,
  paperclip_issue_id TEXT,
  paperclip_identifier TEXT,
  email_id BIGINT,
  reminder_id BIGINT,
  conversation_id UUID,
  assigned_agent TEXT,
  clarification_questions TEXT[] DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT tasks_status_chk CHECK (
    status IN ('pending', 'in_progress', 'blocked', 'completed', 'cancelled', 'deferred')
  ),
  CONSTRAINT tasks_priority_chk CHECK (
    priority IN ('low', 'medium', 'high', 'urgent')
  ),
  CONSTRAINT tasks_source_chk CHECK (
    source IN ('manual', 'gmail', 'chatgpt_archive', 'paperclip', 'hermes', 'reminder')
  )
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON ops.tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_business ON ops.tasks (business_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON ops.tasks (due_at)
  WHERE completed_at IS NULL;

-- ---------------------------------------------------------------------------
-- Extend emails + reminders (additive; safe on existing installs)
-- ---------------------------------------------------------------------------
ALTER TABLE ops.emails
  ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES ops.businesses(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS person_id UUID REFERENCES ops.people(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS place_id UUID REFERENCES ops.places(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS mailbox TEXT DEFAULT 'clawsums@gmail.com',
  ADD COLUMN IF NOT EXISTS review_status TEXT DEFAULT 'unreviewed',
  ADD COLUMN IF NOT EXISTS review_notes TEXT,
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS analysis_summary TEXT,
  ADD COLUMN IF NOT EXISTS analysis_intent TEXT,
  ADD COLUMN IF NOT EXISTS analysis_recommendation TEXT,
  ADD COLUMN IF NOT EXISTS analysis_priority TEXT,
  ADD COLUMN IF NOT EXISTS analysis_json JSONB,
  ADD COLUMN IF NOT EXISTS analysis_report TEXT;

DO $$ BEGIN
  ALTER TABLE ops.emails
    ADD CONSTRAINT emails_review_status_chk CHECK (
      review_status IN ('unreviewed', 'reviewed', 'needs_boss', 'ignored')
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  ALTER TABLE ops.emails
    ADD CONSTRAINT emails_analysis_priority_chk CHECK (
      analysis_priority IS NULL OR analysis_priority IN ('low', 'medium', 'high', 'urgent', 'noise')
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_emails_business ON ops.emails (business_id);
CREATE INDEX IF NOT EXISTS idx_emails_person ON ops.emails (person_id);
CREATE INDEX IF NOT EXISTS idx_emails_review ON ops.emails (review_status);
CREATE INDEX IF NOT EXISTS idx_emails_mailbox ON ops.emails (mailbox);
CREATE INDEX IF NOT EXISTS idx_emails_analysis_priority ON ops.emails (analysis_priority);

-- One durable review row per email (full report history optional via analyzed_at)
CREATE TABLE IF NOT EXISTS ops.email_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id BIGINT NOT NULL REFERENCES ops.emails(id) ON DELETE CASCADE,
  gmail_id TEXT,
  mailbox TEXT DEFAULT 'clawsums@gmail.com',
  business_slug TEXT,
  person_email TEXT,
  review_status TEXT NOT NULL,
  priority TEXT,
  is_noise BOOLEAN DEFAULT false,
  action_required BOOLEAN DEFAULT false,
  intent TEXT,
  summary TEXT NOT NULL,
  recommendation TEXT,
  questions TEXT[] DEFAULT '{}',
  signals TEXT[] DEFAULT '{}',
  linked_task_id UUID,
  report_markdown TEXT NOT NULL,
  analysis_json JSONB,
  analyzed_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (email_id)
);

CREATE INDEX IF NOT EXISTS idx_email_reviews_analyzed ON ops.email_reviews (analyzed_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_reviews_action ON ops.email_reviews (action_required)
  WHERE action_required;

COMMENT ON TABLE ops.email_reviews IS 'Per-email review+analysis report for clawsums@gmail.com inbox';
COMMENT ON COLUMN ops.emails.analysis_report IS 'Latest markdown analysis report for this message';
COMMENT ON COLUMN ops.emails.mailbox IS 'Default clawsums@gmail.com admin inbox';
COMMENT ON COLUMN ops.emails.review_status IS 'Full-inbox review state for CEO/Hermes pass';

ALTER TABLE ops.reminders
  ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES ops.businesses(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS person_id UUID REFERENCES ops.people(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS place_id UUID REFERENCES ops.places(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS task_id UUID REFERENCES ops.tasks(id) ON DELETE SET NULL;

ALTER TABLE ops.reminders DROP CONSTRAINT IF EXISTS reminders_source_check;
ALTER TABLE ops.reminders ADD CONSTRAINT reminders_source_check CHECK (
  source IN ('manual', 'gmail', 'paperclip', 'telegram', 'email', 'chatgpt_archive', 'hermes')
);

COMMENT ON TABLE ops.people IS 'Clawsum CRM people — email identity for triage + Hermes drive';
COMMENT ON TABLE ops.places IS 'Offices, properties, venues linked to cells and people';
COMMENT ON TABLE ops.tasks IS 'Local overwatch task mirror; Paperclip issues remain execution truth';
