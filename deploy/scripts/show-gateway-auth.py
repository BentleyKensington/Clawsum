#!/usr/bin/env python3
import json
from pathlib import Path

c = json.loads(Path("/docker/clawsum/data/.openclaw/openclaw.json").read_text())
print(json.dumps(c.get("gateway", {}), indent=2)[:3000])
