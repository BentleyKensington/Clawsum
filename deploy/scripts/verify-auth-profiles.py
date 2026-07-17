#!/usr/bin/env python3
"""Verify auth-profiles.json exists for all Clawsum OpenClaw agents."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

ROOT = Path("/docker/clawsum/data/.openclaw")
AGENTS = ghl.all_clawsum_openclaw_agent_ids()


def main() -> None:
    ok = True
    for agent_id in AGENTS:
        auth = ROOT / "agents" / agent_id / "agent" / "auth-profiles.json"
        if not auth.exists():
            print(f"MISSING {agent_id}")
            ok = False
            continue
        data = json.loads(auth.read_text())
        profiles = list((data.get("profiles") or {}).keys())
        print(f"OK {agent_id}: {profiles}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
