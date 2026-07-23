#!/usr/bin/env python3
"""Seed ops.businesses cell profiles (no secrets)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2: pip install psycopg2-binary", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"

CELLS = [
    {
        "slug": "personal-admin",
        "name": "Personal Admin",
        "type": "personal",
        "description": "Gmail, calendar, personal docs, ChatGPT archive access",
        "systems_connected": ["gmail", "calendar", "obsidian"],
        "allowed_reads": ["schedule", "inbox_summaries", "task_history"],
        "allowed_actions": ["draft_email", "draft_text", "meeting_summary"],
        "approval_required": ["send_email", "send_text", "calendar_invite"],
        "never_autonomous": ["banking", "legal_filings", "payroll", "credential_changes"],
        "daily_summary_fields": ["inbox_highlights", "calendar", "pending_approvals"],
        "primary_agent": "admin",
        "memory_namespace": "personal-admin",
    },
    {
        "slug": "hardware-local-ai",
        "name": "Hardware / Local AI",
        "type": "infrastructure",
        "description": "Local GPUs, model servers, Vocalitic-adjacent compute stewardship",
        "systems_connected": ["docker", "gpu", "model_servers"],
        "allowed_reads": ["uptime", "vram", "latency", "errors"],
        "allowed_actions": ["diagnostics", "draft_deploy_plan"],
        "approval_required": ["restart_container", "production_deploy", "model_change"],
        "never_autonomous": ["wipe_logs", "delete_call_data", "rotate_prod_credentials"],
        "daily_summary_fields": ["uptime", "vram", "errors"],
        "primary_agent": "coding",
        "memory_namespace": "hardware-local-ai",
    },
    {
        "slug": "wnn-client",
        "name": "WNN / Client",
        "type": "client",
        "description": "WNN Properties — GHL/CloseBot lead qualify and route",
        "systems_connected": ["ghl", "closebot", "hyros", "klaviyo"],
        "allowed_reads": ["lead_status", "conversations", "pipeline", "appointments"],
        "allowed_actions": ["draft_sms", "draft_email", "workshop_invite"],
        "approval_required": ["send_sms", "send_email", "campaign_change", "bulk_contact_update"],
        "never_autonomous": ["delete_contacts", "billing_change", "full_db_export"],
        "daily_summary_fields": ["new_leads", "dropped_conversations", "booked_calls", "urgent"],
        "primary_agent": "ghl",
        "memory_namespace": "wnn-client",
    },
    {
        "slug": "roofing-os",
        "name": "Roofing OS",
        "type": "product",
        "description": "CEOroof / roofing OS — storm intel, leads, field ops",
        "systems_connected": ["crm", "storm_data", "ghl"],
        "allowed_reads": ["storm_reports", "lead_status", "agent_performance"],
        "allowed_actions": ["draft_outreach", "estimator_notes", "lead_summary"],
        "approval_required": ["send_outreach", "paid_data_order", "crm_automation_change"],
        "never_autonomous": ["legal_insurance_claims", "financial_commitments", "delete_customers"],
        "daily_summary_fields": ["storms", "leads", "approvals"],
        "primary_agent": "realestate",
        "memory_namespace": "roofing-os",
    },
    {
        "slug": "vocalitic",
        "name": "Vocalitic",
        "type": "product",
        "description": "Voice AI infrastructure — SignalWire, STT/TTS/LLM, latency",
        "systems_connected": ["signalwire", "local_stt_tts", "call_logs"],
        "allowed_reads": ["server_health", "call_status", "latency", "errors", "cost_estimates"],
        "allowed_actions": ["diagnostics", "draft_deploy_recommendations"],
        "approval_required": ["restart_noncritical", "production_deploy", "model_change"],
        "never_autonomous": ["delete_call_data", "prod_credential_change", "wipe_logs"],
        "daily_summary_fields": ["uptime", "latency", "errors", "call_quality"],
        "primary_agent": "coding",
        "memory_namespace": "vocalitic",
    },
    {
        "slug": "techtasia",
        "name": "Techtasia",
        "type": "business",
        "description": "Techtasia product / company cell",
        "systems_connected": [],
        "allowed_reads": ["status", "tasks"],
        "allowed_actions": ["drafts", "summaries"],
        "approval_required": ["client_comms", "production_change"],
        "never_autonomous": ["billing", "delete_production_data"],
        "daily_summary_fields": ["priorities", "risks", "approvals"],
        "primary_agent": "planning",
        "memory_namespace": "techtasia",
    },
    {
        "slug": "acceptai-fastbuy",
        "name": "AcceptAI / FastBuy",
        "type": "commerce",
        "description": "AcceptAI / FastBuy commerce cell",
        "systems_connected": [],
        "allowed_reads": ["orders_summary", "funnel"],
        "allowed_actions": ["drafts", "reports"],
        "approval_required": ["customer_comms", "pricing_change", "paid_ads"],
        "never_autonomous": ["refunds_bulk", "payout_changes"],
        "daily_summary_fields": ["revenue", "issues", "approvals"],
        "primary_agent": "comms",
        "memory_namespace": "acceptai-fastbuy",
    },
    {
        "slug": "real-estate",
        "name": "Real Estate",
        "type": "business",
        "description": "Owned real-estate acquisitions / ops (non-WNN)",
        "systems_connected": ["postgres_realestate", "arcadedb"],
        "allowed_reads": ["deals", "comps", "pipeline"],
        "allowed_actions": ["draft_outreach", "research_briefs"],
        "approval_required": ["send_outreach", "offers", "contracts"],
        "never_autonomous": ["wire_transfers", "legal_filings", "delete_deals"],
        "daily_summary_fields": ["pipeline", "offers", "risks"],
        "primary_agent": "realestate",
        "memory_namespace": "real-estate",
    },
]


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    path = ENV_FILE if ENV_FILE.exists() else Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if k not in out or not out[k]})
    return out


def connect():
    env = load_env()
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "clawsum"),
    )


UPSERT = """
INSERT INTO ops.businesses (
  name, slug, type, description, systems_connected, allowed_reads, allowed_actions,
  approval_required, never_autonomous, daily_summary_fields, primary_agent,
  memory_namespace, updated_at
) VALUES (
  %(name)s, %(slug)s, %(type)s, %(description)s, %(systems_connected)s, %(allowed_reads)s,
  %(allowed_actions)s, %(approval_required)s, %(never_autonomous)s, %(daily_summary_fields)s,
  %(primary_agent)s, %(memory_namespace)s, now()
)
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  systems_connected = EXCLUDED.systems_connected,
  allowed_reads = EXCLUDED.allowed_reads,
  allowed_actions = EXCLUDED.allowed_actions,
  approval_required = EXCLUDED.approval_required,
  never_autonomous = EXCLUDED.never_autonomous,
  daily_summary_fields = EXCLUDED.daily_summary_fields,
  primary_agent = EXCLUDED.primary_agent,
  memory_namespace = EXCLUDED.memory_namespace,
  updated_at = now()
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="List businesses and exit")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.list:
        conn = connect()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT slug, name, type, active FROM ops.businesses ORDER BY slug"
            )
            rows = cur.fetchall()
        print(json.dumps(rows, indent=2, default=str))
        return

    if args.dry_run:
        print(json.dumps([c["slug"] for c in CELLS], indent=2))
        return

    conn = connect()
    with conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            for cell in CELLS:
                cur.execute(UPSERT, cell)
                print(f"upserted {cell['slug']}")
    print(f"OK {len(CELLS)} business cells")


if __name__ == "__main__":
    main()
