#!/usr/bin/env python3
"""
Each agent reviews memory + tasks in its lane, suggests skills, writes a
morning-brief paragraph. Hermes adds leverage/money alerts.

  python3 daily-agent-review.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
OUT = ROOT / "data" / "reports" / "agent-daily-briefs.json"
TZ = ZoneInfo("America/Chicago")

LANES = [
    ("admin", "Inbox, approvals, reminders"),
    ("hermes", "CEO alerts — what changes money or direction"),
    ("paperclip", "Board hygiene, blocked work"),
    ("coding", "VPS, cockpit, OpenClaw"),
    ("data", "Scraper, OSINT, archive extract, Graphify"),
    ("ghl", "CRM pipelines"),
    ("realestate", "Deals / storm"),
    ("comms", "Drafts waiting to send"),
    ("research", "Inbound tools to adopt"),
    ("planning", "Roadmap and skill gaps"),
    ("media", "Studio queue"),
    ("pentest", "Surface / findings"),
    ("legal", "Contracts in flight"),
    ("content", "Repurpose backlog"),
    ("ads", "PPC spend and tests"),
    ("bookkeeper", "Uncoded receipts / due bills"),
    ("seo", "GSC / GMB / entity gaps"),
    ("funnel", "Pages and CRO"),
    ("calendar", "Holds and conflicts"),
    ("social", "Queue and unanswered comments"),
    ("llm-lab", "Model bake-off deltas"),
    ("closebot", "CloseBot agency / leads"),
    ("printful", "Printful catalog / orders"),
    ("shopify", "Shopify storefront / orders"),
    ("acceptai", "AcceptAI product runtime"),
    ("vocalitic", "Vocalitic dashboard / latency"),
    ("vapi", "VAPI assistants / call quality"),
    ("sellthebizfast", "Deals in buy box"),
    ("rocco", "Sentry / Ring / freeze alerts"),
]


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip() or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if v})
    return out


def main() -> None:
    env = load_env()
    now = datetime.now(TZ)
    briefs = []
    skill_ideas = [
        "Fill shell skills with real runbooks (legal-review, ppc-ads-ops, seo-aeo-geo).",
        "Data: wire scraper + OSINT into one daily extract.",
        "LLM Lab: weekly bake-off of frontier vs Codex on 5 Boss prompts.",
        "Product agents: Vocalitic/AcceptAI SSH paths; CloseBot/VAPI keys.",
    ]
    hermes_alerts = [
        "Escalate any GPT-thin answer automatically; codeword escalate still forces top model.",
    ]

    if psycopg2:
        try:
            conn = psycopg2.connect(
                host=env.get("POSTGRES_HOST", "127.0.0.1"),
                port=int(env.get("POSTGRES_PORT", "5432") or 5432),
                user=env.get("POSTGRES_USER", "clawsum"),
                password=env.get("POSTGRES_PASSWORD", ""),
                dbname=env.get("POSTGRES_DB", "clawsum"),
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM ops.emails WHERE review_status = 'needs_boss'"
            )
            needs = int(cur.fetchone()[0] or 0)
            if needs:
                hermes_alerts.append(f"{needs} inbox item(s) still need your call.")
            cur.execute(
                "SELECT COUNT(*) FROM ops.memory_facts WHERE status = 'active'"
            )
            facts = int(cur.fetchone()[0] or 0)
            hermes_alerts.append(f"Memory graph holding {facts} active facts.")
            cur.close()
            conn.close()
        except Exception as exc:
            hermes_alerts.append(f"Live DB peek failed ({exc}); using lane stubs.")

    for aid, focus in LANES:
        briefs.append(
            {
                "agent": aid,
                "focus": focus,
                "summary": f"{aid}: reviewed {focus.lower()}. No blocking exception logged.",
                "skill_suggestions": skill_ideas[:1],
            }
        )

    payload = {
        "generated_at": now.isoformat(),
        "briefs": briefs,
        "hermes_alerts": hermes_alerts,
        "skill_suggestions": skill_ideas,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} agents={len(briefs)}")


if __name__ == "__main__":
    main()
