#!/usr/bin/env python3
import json
from pathlib import Path

c = json.loads(Path("/docker/clawsum/data/.openclaw/openclaw.json").read_text())
for key in ("channels", "plugins", "hooks", "skills"):
    if key in c:
        print(f"=== {key} ===")
        print(json.dumps(c[key], indent=2)[:2000])
        print()
