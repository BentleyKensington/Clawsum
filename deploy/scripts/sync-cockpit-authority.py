#!/usr/bin/env python3
"""
Source of truth → authority.json + missing SKILL.md shells.

Team/Skills pages read authority.json (stale = 'only 10 skills').
Run after adding agents/skills; install-clawsum-sidebar-plugins.sh calls this.

  python3 sync-cockpit-authority.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
AUTH_OUT = (
    ROOT
    / "examples"
    / "hermes-cockpit"
    / "plugin"
    / "clawsum-cockpit"
    / "dashboard"
    / "authority.json"
)

AGENTS = [
    ("admin", "Clawsum Admin", ["clawsum-platform", "personal-admin"], "Brief, inbox, approvals, reminders", "Command liaison."),
    ("hermes", "Clawsum", ["clawsum-platform", "personal-admin"], "CEO face, daily alerts, archive", "Jarvis — talks, alerts, escalates."),
    ("paperclip", "Clawsum Paperclip", ["clawsum-platform"], "Board hygiene", "Tasks and gates."),
    ("coding", "Clawsum Coding", ["clawsum-platform", "hardware-local-ai", "vocalitic"], "VPS, cockpit, OpenClaw", "Platform engineer."),
    ("data", "Clawsum Data", ["clawsum-platform"], "Postgres, ETL, scraper, OSINT, Graphify", "Data plane + collection tools."),
    ("ghl", "Clawsum GHL", ["wnn-client"], "CRM pipelines", "GoHighLevel ops."),
    ("realestate", "Clawsum RE", ["real-estate", "roofing-os"], "Deals, storm intel", "RE + roofing research."),
    ("comms", "Clawsum Comms", ["acceptai-fastbuy"], "Outbound drafts", "Drafts only; send Tier 2."),
    ("research", "Clawsum Research", ["*"], "Competitive briefs", "Read-heavy research."),
    ("planning", "Clawsum Planning", ["techtasia", "clawsum-platform"], "Roadmap", "Priorities and cells."),
    ("media", "Clawsum Media", ["media-production", "hardware-local-ai"], "Studio render/publish", "Video factory; publish Tier 2."),
    ("pentest", "Clawsum Pentest", ["clawsum-platform"], "Defensive security", "Scans and reports; no exploits."),
    ("legal", "Clawsum Legal", ["clawsum-platform", "personal-admin"], "Contracts, terms, privilege", "Draft/review only; file/sign Tier 3."),
    ("content", "Clawsum Content", ["media-production", "clawsum-platform"], "Repurpose longform → shorts/posts", "Cuts and drafts; post via Social."),
    ("ads", "Clawsum Ads", ["acceptai-fastbuy", "wnn-client"], "PPC / paid media", "Budgets and ads; spend Tier 2."),
    ("bookkeeper", "Clawsum Bookkeeper", ["clawsum-platform", "personal-admin"], "Books, invoices, receipts", "Ledger hygiene; pay/wire Tier 3."),
    ("seo", "Clawsum SEO", ["clawsum-platform", "media-production"], "SEO/AEO/GEO, GSC, GMB, knowledge panel", "Rankings and entities."),
    ("funnel", "Clawsum Funnel", ["clawsum-platform", "acceptai-fastbuy"], "Offers, pages, CRO", "Funnel builder."),
    ("calendar", "Clawsum Calendar", ["personal-admin", "clawsum-platform"], "Scheduling across cells", "Holds and invites; send Tier 2."),
    ("social", "Clawsum Social", ["media-production", "clawsum-platform"], "Post, schedule, reply", "Public voice; post/reply Tier 2."),
    ("llm-lab", "Clawsum LLM Lab", ["clawsum-platform"], "Model bake-offs + weekly vendor watch", "Tests and compares LLMs; no silent spend."),
    ("closebot", "CloseBot", ["wnn-client"], "CloseBot agency API", "Leads/bots; send = Tier 2."),
    ("printful", "Printful", ["acceptai-fastbuy"], "Printful catalog / fulfill", "Live catalog = Tier 2."),
    ("shopify", "Shopify", ["acceptai-fastbuy"], "Shopify admin", "Theme/payments = Tier 2."),
    ("acceptai", "AcceptAI", ["acceptai-fastbuy"], "AcceptAI product runtime", "SSH/API; deploy = Tier 2."),
    ("vocalitic", "Vocalitic", ["vocalitic", "hardware-local-ai"], "Vocalitic product", "v1m12 + SSH; deploy = Tier 2."),
    ("vapi", "VAPI", ["vocalitic", "clawsum-platform"], "VAPI org", "Outbound/buy number = Tier 2."),
    ("sellthebizfast", "SellTheBizFast", ["sellthebizfast"], "Buy-side acquisitions", "Outbound/LOI gated."),
    ("rocco", "Rocco Secure", ["clawsum-platform"], "Sentry + official Ring", "No exploits; Ring official API only."),
]

SHELLS = [
    ("data-scraper", ["data"], ["clawsum-platform"], 1, ["BRIGHTDATA_*", "POSTGRES_*"], "Run the in-house scraper as a Data tool — not its own agent."),
    ("data-osint", ["data", "pentest"], ["clawsum-platform"], 0, ["POSTGRES_*"], "OSINT + global monitoring; extract pertinent public details."),
    ("data-chat-extract", ["data", "hermes"], ["clawsum-platform"], 1, ["POSTGRES_*"], "Pull durable facts from chat/archive into memory (skip personal)."),
    ("graphify-obsidian", ["data", "research", "hermes"], ["clawsum-platform"], 1, ["POSTGRES_*", "ARCADEDB_*"], "Graphify / 3D Obsidian memory visualizer."),
    ("agent-daily-review", ["hermes", "admin", "planning"], ["*"], 1, ["PAPERCLIP_*", "POSTGRES_*"], "Each agent reviews memory, tasks, research; suggests skills; feeds morning brief."),
    ("hermes-daily-alert", ["hermes", "admin"], ["clawsum-platform"], 1, ["TELEGRAM_*", "DISCORD_*", "POSTGRES_*"], "Hermes daily sweep — money saved, leverage, must-know alerts."),
    ("legal-review", ["legal", "admin"], ["clawsum-platform"], 0, [], "Contract/terms review. File/sign = Tier 3."),
    ("content-repurpose", ["content", "media"], ["media-production"], 1, ["MINIO_*", "PAPERCLIP_*"], "Longform → clips, threads, posts. Publish via Social/Media."),
    ("ppc-ads-ops", ["ads", "comms"], ["acceptai-fastbuy", "wnn-client"], 1, [], "PPC campaigns. Spend = Tier 2."),
    ("bookkeeper-ledger", ["bookkeeper", "admin"], ["clawsum-platform"], 0, [], "Invoices, receipts, books. Pay/wire = Tier 3."),
    ("seo-aeo-geo", ["seo", "research"], ["clawsum-platform"], 1, [], "GSC, GMB, knowledge panel, AEO/GEO. Public change = Tier 2."),
    ("funnel-builder", ["funnel", "comms", "coding"], ["clawsum-platform"], 1, ["SSH"], "Offers, landing pages, CRO. Prod publish = Tier 2."),
    ("calendar-ops", ["calendar", "admin"], ["personal-admin", "clawsum-platform"], 1, [], "Holds and scheduling. Invite send = Tier 2."),
    ("social-posting", ["social", "content", "comms"], ["media-production"], 1, [], "Schedule posts and reply to comments. Post/reply = Tier 2."),
    ("llm-compare", ["llm-lab", "coding", "research"], ["clawsum-platform"], 1, ["OPENAI_*", "OPENROUTER_*"], "Bake-off models; write scorecard. Paid eval = notify Boss."),
    ("cockpit-hud", ["coding", "hermes", "admin"], ["clawsum-platform"], 1, [], "CEO cockpit HUD — gauges, marquee, live tiles."),
    ("inbound-adopt-evaluate", ["research", "planning", "hermes", "admin", "coding"], ["clawsum-platform", "techtasia"], 1, ["OPENAI_*"], "Evaluate inbound tools/mockups for adopt."),
    ("skill-forge", ["coding", "planning", "admin", "hermes"], ["clawsum-platform", "techtasia"], 1, ["PAPERCLIP_*"], "Turn adopt/steal into a SKILL.md."),
    ("discord-hq", ["admin", "comms", "coding", "social"], ["clawsum-platform"], 1, ["DISCORD_*"], "Discord HQ notify/bindings."),
    ("ghl-weekly-rei-report", ["ghl", "admin"], ["wnn-client"], 1, ["GHL_*", "POSTGRES_*"], "Weekly REI GHL report."),
    ("pentest-threat-model", ["pentest", "admin", "coding"], ["clawsum-platform"], 0, ["PAPERCLIP_*", "POSTGRES_*"], "Living threat register."),
    ("pentest-surface-scan", ["pentest", "coding", "data"], ["clawsum-platform"], 1, ["POSTGRES_*"], "Read-only surface scan."),
    ("pentest-report", ["pentest", "admin"], ["clawsum-platform"], 1, ["POSTGRES_*", "MINIO_*"], "Security reports."),
    ("pentest-notify", ["pentest", "admin"], ["clawsum-platform"], 1, ["DISCORD_*", "TELEGRAM_*"], "High/Critical notify."),
]


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end]
    data: dict = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def write_shell(sid: str, agents: list[str], cells: list[str], tier: int, creds: list[str], desc: str) -> None:
    folder = SKILLS / sid
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "SKILL.md"
    if path.exists() and path.stat().st_size > 80:
        return
    cred = ", ".join(creds) if creds else ""
    path.write_text(
        f"""---
name: {sid}
description: {desc}
agents: [{", ".join(agents)}]
cells: [{", ".join(cells)}]
tier_autonomous: {tier}
credentials: [{cred}]
approval_actions: []
status: shell
---

# {sid}

**Status:** shell — populate runbooks as the agent learns.

## When to use

{desc}

## Instructions

1. Read related memory + open Paperclip issues for this domain.
2. Draft the next move; do not take Tier 2+ actions.
3. Suggest skill improvements on the daily review.

## Escalation

Tier 2+ (send, spend, legal file, pay) → Boss Approve All.
""",
        encoding="utf-8",
    )


def scan_skills() -> list[dict]:
    out: list[dict] = []
    if not SKILLS.is_dir():
        return out
    for folder in sorted(SKILLS.iterdir()):
        md = folder / "SKILL.md"
        if not folder.is_dir() or not md.is_file():
            continue
        if folder.name.startswith("_"):
            continue
        fm = parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
        agents = re.findall(r"[a-z0-9-]+", fm.get("agents", ""))
        cells = re.findall(r"[a-z0-9*_-]+", fm.get("cells", "")) or ["clawsum-platform"]
        try:
            tier = int(fm.get("tier_autonomous", "1") or 1)
        except ValueError:
            tier = 1
        creds = re.findall(r"[A-Z0-9_*]+", fm.get("credentials", ""))
        out.append(
            {
                "id": fm.get("name") or folder.name,
                "agents": agents or ["admin"],
                "cells": cells,
                "tier": tier,
                "credentials": creds,
                "description": fm.get("description") or "",
            }
        )
    return out


def main() -> None:
    SKILLS.mkdir(parents=True, exist_ok=True)
    for sid, agents, cells, tier, creds, desc in SHELLS:
        write_shell(sid, agents, cells, tier, creds, desc)

    skills = scan_skills()
    agents = [
        {
            "id": i,
            "name": n,
            "cells": cells,
            "domains": d,
            "blurb": b,
        }
        for i, n, cells, d, b in AGENTS
    ]
    projects = [
        {"id": "clawsum-platform", "name": "Clawsum Platform", "kind": "cell", "blurb": "Ops + cockpit."},
        {"id": "personal-admin", "name": "Personal Admin", "kind": "cell", "blurb": "Gerald private lane."},
        {"id": "wnn-client", "name": "WNN / GHL", "kind": "cell", "blurb": "CRM."},
        {"id": "real-estate", "name": "Real Estate", "kind": "cell", "blurb": "Deals."},
        {"id": "roofing-os", "name": "Roofing OS", "kind": "cell", "blurb": "Storm intel."},
        {"id": "techtasia", "name": "Techtasia", "kind": "cell", "blurb": "Roadmap."},
        {"id": "acceptai-fastbuy", "name": "AcceptAI / FastBuy", "kind": "cell", "blurb": "Commerce."},
        {"id": "vocalitic", "name": "Vocalitic", "kind": "cell", "blurb": "Product runtime."},
        {"id": "hardware-local-ai", "name": "Hardware / Local AI", "kind": "cell", "blurb": "GPU / local models."},
        {"id": "media-production", "name": "Media Production", "kind": "cell", "blurb": "Studio."},
        {"id": "sellthebizfast", "name": "SellTheBizFast", "kind": "cell", "blurb": "Acquisitions."},
    ]
    payload = {
        "source": "sync-cockpit-authority.py + deploy/skills/*/SKILL.md",
        "agents": agents,
        "skills": skills,
        "tiers": {
            "0": "Read-only / summarize — auto ok",
            "1": "Drafts / local writes — auto ok",
            "2": "Send / prod / spend — Boss approval",
            "3": "Banking / wipe / rotate — human only",
        },
        "primary_skills": [
            "ceo-daily-brief",
            "agent-daily-review",
            "hermes-daily-alert",
            "gmail-inbox-review",
            "overwatch-approvals",
        ],
        "projects": projects,
        "agent_count": len(agents),
        "skill_count": len(skills),
    }
    AUTH_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUTH_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"agents={len(agents)} skills={len(skills)} wrote {AUTH_OUT}")


if __name__ == "__main__":
    main()
