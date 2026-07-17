#!/usr/bin/env python3
"""Build Telegram group bindings from OpenClaw session store (subject/title)."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
AGENTS = Path("/docker/clawsum/data/.openclaw/agents")


def collect_groups():
    groups = {}
    for sessions_file in AGENTS.glob("*/sessions/sessions.json"):
        try:
            data = json.loads(sessions_file.read_text())
        except Exception:
            continue
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            gid = entry.get("groupId")
            subject = entry.get("subject") or entry.get("origin", {}).get("label", "")
            if gid and ("group" in key or entry.get("chatType") == "group"):
                groups[str(gid)] = subject or groups.get(str(gid), "")
    return groups


def main():
    groups = collect_groups()
    if not groups:
        print("NO_GROUPS_IN_SESSIONS")
        return

    cfg = json.loads(CONFIG.read_text())
    existing = {
        (
            b.get("agentId"),
            b.get("match", {}).get("peer", {}).get("id"),
        )
        for b in cfg.get("bindings", [])
        if isinstance(b, dict)
    }

    bindings = list(cfg.get("bindings") or [])
    added = 0
    for gid, title in sorted(groups.items(), key=lambda x: x[1].lower()):
        agent = ghl.match_telegram_agent(title)
        if not agent:
            print(f"UNMATCHED\t{title}\t{gid}")
            continue
        key = (agent, gid)
        if key in existing:
            print(f"SKIP\t{title}\t{gid}\t->\t{agent}")
            continue
        bindings.append(
            {
                "agentId": agent,
                "match": {
                    "channel": "telegram",
                    "peer": {"kind": "group", "id": gid},
                },
            }
        )
        existing.add(key)
        added += 1
        print(f"OK\t{title}\t{gid}\t->\t{agent}")

    cfg["bindings"] = bindings
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Total bindings: {len(bindings)} (+{added} new)")


if __name__ == "__main__":
    main()
