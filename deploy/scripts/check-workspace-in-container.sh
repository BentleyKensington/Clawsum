#!/bin/bash
set -euo pipefail
for a in coding data ghl comms planning admin; do
  docker exec clawsum-openclaw-gateway-1 ls -la "/home/node/.openclaw/workspace-${a}/SOUL.md" 2>/dev/null || echo "MISSING $a"
done
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
cfg = json.loads(p.read_text())
agents = cfg.get("agents", {}).get("list", [])
for a in agents:
    if a.get("id") in ("coding","data","ghl","comms","planning","admin"):
        print(a["id"], a.get("workspace"))
PY
