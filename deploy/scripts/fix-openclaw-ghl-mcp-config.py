#!/usr/bin/env python3
"""Fix openclaw.json: remove invalid mcpServers from agents.list (2026.5.x)."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import ghl_accounts as ghl

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")


def main():
    cfg = json.loads(CONFIG.read_text())
    changed = 0
    for a in cfg.get("agents", {}).get("list", []):
        if "mcpServers" in a:
            del a["mcpServers"]
            changed += 1
    servers = (cfg.get("mcp") or {}).get("servers") or {}
    for acc in ghl.accounts():
        name = acc["mcp_server"]
        agent_id = acc["id"]
        if name in servers and isinstance(servers[name], dict):
            codex = servers[name].setdefault("codex", {})
            codex["agents"] = [agent_id]
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Fixed {changed} agents; wrote {CONFIG}")

if __name__ == "__main__":
    main()
