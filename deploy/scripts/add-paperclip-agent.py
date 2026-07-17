#!/usr/bin/env python3
"""Add paperclip agent and Telegram group binding."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from instance_config import telegram_paperclip_group_id  # noqa: E402

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
WORKSPACE = Path("/docker/clawsum/data/.openclaw/workspace-paperclip")

AGENT = {
    "id": "paperclip",
    "name": "Paperclip",
    "workspace": "/home/node/.openclaw/workspace-paperclip",
    "tools": {
        "allow": [
            "read",
            "write",
            "edit",
            "sessions_list",
            "sessions_history",
            "session_status",
        ],
        "deny": ["exec"],
    },
}

DATABASE_MD = """# DATABASE.md — paperclip agent

**Database:** `clawsum` (orchestration metadata; Paperclip service owns task state)
**Host:** `postgres:5432` (Docker network `clawsum`)
**User:** `clawsum`
**Primary schema:** `ops`

Paperclip UI/API: `http://paperclip:3100` (compose profile `orchestration`)

## Role

- Route long-running work across specialist agents via Paperclip tasks.
- Do not query `realestate` or `ghl` databases directly — delegate to those agents.
"""


def main():
    group_id = telegram_paperclip_group_id()
    cfg = json.loads(CONFIG.read_text())
    agents = cfg.setdefault("agents", {}).setdefault("list", [])
    ids = {a["id"] for a in agents if isinstance(a, dict) and a.get("id")}
    if "paperclip" not in ids:
        agents.append(AGENT)
        print("Added paperclip agent")
    else:
        print("paperclip agent already present")

    bindings = cfg.setdefault("bindings", [])
    binding = {
        "agentId": "paperclip",
        "match": {
            "channel": "telegram",
            "peer": {"kind": "group", "id": group_id},
        },
    }
    exists = any(
        b.get("agentId") == "paperclip"
        and b.get("match", {}).get("peer", {}).get("id") == group_id
        for b in bindings
        if isinstance(b, dict)
    )
    if not exists:
        bindings.append(binding)
        print(f"Bound Paperclip group ({group_id}) -> paperclip")
    else:
        print("Binding already exists")

    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "DATABASE.md").write_text(DATABASE_MD)
    print("Wrote workspace-paperclip/DATABASE.md")


if __name__ == "__main__":
    main()
