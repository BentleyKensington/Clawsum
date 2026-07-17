#!/usr/bin/env python3
"""Extract telegram group session keys from OpenClaw sessions.json."""
import json
import re
from pathlib import Path

sessions = Path("/docker/clawsum/data/.openclaw/agents/main/sessions/sessions.json")
if not sessions.exists():
    print("NO_SESSIONS_FILE")
    raise SystemExit(0)

data = json.loads(sessions.read_text())
for key in sorted(data.keys()):
    if "telegram" in key and "group" in key:
        print(key)

# Also scan all agent session dirs
for p in Path("/docker/clawsum/data/.openclaw/agents").glob("*/sessions/sessions.json"):
    try:
        d = json.loads(p.read_text())
        for key in d:
            if "telegram" in key and "group" in key:
                print(f"{p.parent.parent.name}: {key}")
    except Exception:
        pass
