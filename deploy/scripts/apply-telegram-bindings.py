#!/usr/bin/env python3
"""Fetch Telegram groups and write OpenClaw bindings."""
import json
import re
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
ENV = Path("/docker/clawsum/.env")


def fetch_chats():
    env = ENV.read_text()
    m = re.search(r"^TELEGRAM_BOT_TOKEN=(.+)$", env, re.M)
    token = m.group(1).strip()
    url = f"https://api.telegram.org/bot{token}/getUpdates?limit=100"
    with urllib.request.urlopen(url) as r:
        data = json.load(r)
    chats = {}
    for u in data.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        c = msg.get("chat") or {}
        if c.get("type") in ("group", "supergroup") and c.get("title"):
            chats[c["id"]] = c["title"]
    return chats


def main():
    chats = fetch_chats()
    if not chats:
        print("NO_GROUPS")
        return

    cfg = json.loads(CONFIG.read_text())
    bindings = []
    matched = []
    for cid, title in chats.items():
        agent = ghl.match_telegram_agent(title)
        if not agent:
            print(f"UNMATCHED\t{title}\t{cid}")
            continue
        bindings.append({
            "agentId": agent,
            "match": {
                "channel": "telegram",
                "peer": {"kind": "group", "id": str(cid)},
            },
        })
        matched.append((title, cid, agent))
        print(f"OK\t{title}\t{cid}\t->\t{agent}")

    cfg["bindings"] = bindings
    cfg.setdefault("channels", {}).setdefault("telegram", {})["enabled"] = True
    cfg["plugins"]["entries"]["telegram"] = {"enabled": True}
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Wrote {len(bindings)} bindings")

if __name__ == "__main__":
    main()
