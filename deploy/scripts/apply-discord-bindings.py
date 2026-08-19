#!/usr/bin/env python3
"""Apply OpenClaw Discord bindings from discord-hq-map.json (one agent per channel)."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
MAP = Path("/docker/clawsum/data/discord-hq-map.json")


def main() -> int:
    if not MAP.exists():
        raise SystemExit(f"missing {MAP} — run discord-provision-hq.py first")
    if not CONFIG.exists():
        raise SystemExit(f"missing {CONFIG}")

    data = json.loads(MAP.read_text(encoding="utf-8"))
    guild = data.get("guild_id")
    channels = data.get("channels") or {}

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    bindings = cfg.setdefault("bindings", [])

    # Drop prior discord peer bindings; keep telegram/other
    kept = [
        b
        for b in bindings
        if not (
            isinstance(b, dict)
            and (b.get("match") or {}).get("channel") == "discord"
        )
    ]

    # Must match agents.list IDs in openclaw.json (unknown ids crash the gateway).
    # hermes UI face is not an OpenClaw agent — Discord Jarvis channel routes to admin.
    # GHL uses template agent; instance overlays stay on Telegram until bound.
    agent_channels = {
        "boss_desk": "admin",
        "jarvis": "admin",
        "admin": "admin",
        "paperclip": "paperclip",
        "coding": "coding",
        "data": "data",
        "ghl": "ghl-template",
        "comms": "comms",
        "research": "research",
        "closebot": "closebot",
        "printful": "printful",
        "shopify": "shopify",
        "seo_aeo_geo": "seo-aeo-geo",
        "meta_ads": "meta-ads",
        "acceptai": "acceptai",
        "calendar": "calendar",
        "slack_avenou": "slack-avenou",
        "vocalitic": "vocalitic",
        "llm_lab": "llm-lab",
        "vapi": "vapi",
        "sellthebizfast": "sellthebizfast",
        "rocco": "rocco",
    }
    # Remap stale provision map agent names → live OpenClaw ids
    agent_aliases = {
        "hermes": "admin",
        "ghl": "ghl-template",
    }

    # Validate against live agents.list when present
    live_ids = set()
    for a in (cfg.get("agents") or {}).get("list") or []:
        if isinstance(a, dict) and a.get("id"):
            live_ids.add(str(a["id"]))

    added = 0
    for key, agent in agent_channels.items():
        ch = channels.get(key) or {}
        cid = ch.get("id")
        if not cid:
            print(f"skip {key}: no channel id")
            continue
        # Prefer agent override from map, then alias unknown names
        agent = ch.get("agent") or agent
        agent = agent_aliases.get(str(agent), str(agent))
        if live_ids and agent not in live_ids:
            print(f"skip #{ch.get('name', key)}: agent {agent} not in agents.list")
            continue
        binding = {
            "agentId": agent,
            "match": {
                "channel": "discord",
                "guildId": str(guild),
                "peer": {"kind": "channel", "id": str(cid)},
            },
        }
        kept.append(binding)
        added += 1
        print(f"bind #{ch.get('name', key)} → {agent}")

    cfg["bindings"] = kept
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {added} discord bindings (telegram bindings preserved)")
    print("Restart: docker compose restart openclaw-gateway")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
