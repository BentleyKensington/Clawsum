#!/usr/bin/env python3
import json
import sys
from pathlib import Path

agent = sys.argv[1] if len(sys.argv) > 1 else "main"
p = Path(f"/docker/clawsum/data/.openclaw/agents/{agent}/agent/auth-profiles.json")
if not p.exists():
    print("MISSING", agent)
    raise SystemExit(1)
data = json.loads(p.read_text())
profiles = data.get("profiles") or data
for name, prof in profiles.items():
    if not isinstance(prof, dict):
        continue
    print(
        name,
        "provider=", prof.get("provider"),
        "type=", prof.get("type"),
        "hasKey=", bool(prof.get("key")),
    )
