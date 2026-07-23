-- Clawsum overwatch registry (business cells, approvals, audit)
-- Apply on new installs via postgres-init; on live VPS run once manually.
\c clawsum

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.businesses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  type TEXT,
  description TEXT,
  risk_level TEXT DEFAULT 'normal',
  systems_connected TEXT[] DEFAULT '{}',
  allowed_reads TEXT[] DEFAULT '{}',
  allowed_actions TEXT[] DEFAULT '{}',
  approval_required TEXT[] DEFAULT '{}',
  never_autonomous TEXT[] DEFAULT '{}',
  daily_summary_fields TEXT[] DEFAULT '{}',
  primary_agent TEXT,
  openclaw_gateway TEXT DEFAULT 'default',
  memory_namespace TEXT,
  paperclip_project_id TEXT,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.overwatch_agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES ops.businesses(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  role TEXT,
  paperclip_agent_id TEXT,
  openclaw_agent_id TEXT,
  permission_level TEXT DEFAULT 'standard',
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.approvals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES ops.businesses(id),
  paperclip_issue_id TEXT,
  requested_by TEXT,
  agent_name TEXT,
  action_type TEXT NOT NULL,
  action_summary TEXT NOT NULL,
  reason TEXT,
  risk_level TEXT NOT NULL DEFAULT 'tier_2',
  data_accessed TEXT[] DEFAULT '{}',
  cost_estimate TEXT,
  proposed_output TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  rejected_at TIMESTAMPTZ,
  decision_note TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT approvals_status_chk CHECK (
    status IN ('pending', 'approved', 'rejected', 'revised', 'cancelled')
  ),
  CONSTRAINT approvals_risk_chk CHECK (
    risk_level IN ('tier_0', 'tier_1', 'tier_2', 'tier_3')
  )
);

CREATE INDEX IF NOT EXISTS idx_approvals_status ON ops.approvals (status);
CREATE INDEX IF NOT EXISTS idx_approvals_business ON ops.approvals (business_id);

CREATE TABLE IF NOT EXISTS ops.audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES ops.businesses(id),
  actor_type TEXT,
  actor_name TEXT,
  action TEXT NOT NULL,
  tool_name TEXT,
  target_resource TEXT,
  input_summary TEXT,
  output_summary TEXT,
  approval_id UUID REFERENCES ops.approvals(id),
  paperclip_issue_id TEXT,
  risk_level TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON ops.audit_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_business ON ops.audit_logs (business_id);

COMMENT ON TABLE ops.businesses IS 'CEO overwatch business cell registry — credentials stay in .env/vault';
COMMENT ON TABLE ops.approvals IS 'Risk-tiered Gerald approval queue (Paperclip Phase 3)';
COMMENT ON TABLE ops.audit_logs IS 'Governed action trail for Hermes/Paperclip/OpenClaw';
