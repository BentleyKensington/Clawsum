#!/usr/bin/env python3
"""Dump GHL MCP tools/list for agent capability documentation."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl
from ghl_mcp_client import load_env, mcp_call

env = load_env()
acc = ghl.account_by_slug("ghl")
pit = env[acc["env_pit"]]
loc = env[acc["env_location"]]
resp = mcp_call("tools/list", pit=pit, location_id=loc, compact_limit="100")
# Write full tool list (names only) for doc generation
out = Path("/docker/clawsum/obsidian/GHL/_tools/mcp-tools-ghl.json")
out.parent.mkdir(parents=True, exist_ok=True)
names = resp.get("toolNames") or []
out.write_text(json.dumps({"count": len(names), "tools": names}, indent=2))
print(json.dumps({"count": len(names), "tools": names}, indent=2))
