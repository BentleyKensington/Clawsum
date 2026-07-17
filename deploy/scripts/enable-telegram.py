#!/usr/bin/env python3
import json
from pathlib import Path
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
c = json.loads(p.read_text())
c.setdefault("channels", {}).setdefault("telegram", {})["enabled"] = True
c.setdefault("plugins", {}).setdefault("entries", {})["telegram"] = {"enabled": True}
p.write_text(json.dumps(c, indent=2) + "\n")
print("telegram enabled")
