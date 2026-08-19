#!/usr/bin/env python3
"""Add independent OpenClaw agent lanes for new Discord channels."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")

NEW_AGENTS = [
    {
        "id": "closebot",
        "name": "CloseBot",
        "workspace": "/home/node/.openclaw/workspace-closebot",
        "tools": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "printful",
        "name": "Printful",
        "workspace": "/home/node/.openclaw/workspace-printful",
        "tools": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "shopify",
        "name": "Shopify",
        "workspace": "/home/node/.openclaw/workspace-shopify",
        "tools": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "seo-aeo-geo",
        "name": "SEO AEO GEO",
        "workspace": "/home/node/.openclaw/workspace-seo-aeo-geo",
        "tools": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "meta-ads",
        "name": "Meta Ads",
        "workspace": "/home/node/.openclaw/workspace-meta-ads",
        "tools": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "acceptai",
        "name": "AcceptAI",
        "workspace": "/home/node/.openclaw/workspace-acceptai",
        "tools": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "calendar",
        "name": "Calendar",
        "workspace": "/home/node/.openclaw/workspace-calendar",
        "tools": {"allow": ["read", "write"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "slack-avenou",
        "name": "Slack Avenou",
        "workspace": "/home/node/.openclaw/workspace-slack-avenou",
        "tools": {"allow": ["read", "write"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "vocalitic",
        "name": "Vocalitic",
        "workspace": "/home/node/.openclaw/workspace-vocalitic",
        "tools": {"allow": ["read", "write", "edit", "exec", "browser"], "deny": []},
    },
    {
        "id": "llm-lab",
        "name": "LLM Lab",
        "workspace": "/home/node/.openclaw/workspace-llm-lab",
        "tools": {"allow": ["read", "write", "browser", "exec"], "deny": []},
    },
    {
        "id": "vapi",
        "name": "VAPI",
        "workspace": "/home/node/.openclaw/workspace-vapi",
        "tools": {"allow": ["read", "write", "browser", "exec"], "deny": ["apply_patch"]},
    },
    {
        "id": "sellthebizfast",
        "name": "SellTheBizFast",
        "workspace": "/home/node/.openclaw/workspace-sellthebizfast",
        "tools": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    },
    {
        "id": "rocco",
        "name": "Rocco Secure",
        "workspace": "/home/node/.openclaw/workspace-rocco",
        "tools": {"allow": ["read", "write", "edit", "exec", "browser"], "deny": []},
    },
]


def main() -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    agents = cfg.setdefault("agents", {}).setdefault("list", [])
    by_id = {
        str(a.get("id")): a
        for a in agents
        if isinstance(a, dict) and a.get("id")
    }
    added = 0
    updated = 0
    for spec in NEW_AGENTS:
        if spec["id"] in by_id:
            current = by_id[spec["id"]]
            changed = False
            for key in ("name", "workspace", "tools"):
                if current.get(key) != spec.get(key):
                    current[key] = spec[key]
                    changed = True
            if changed:
                updated += 1
                print(f"updated {spec['id']}")
            else:
                print(f"exists {spec['id']}")
            continue
        agents.append(spec)
        added += 1
        print(f"added {spec['id']}")
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"done added={added} updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
