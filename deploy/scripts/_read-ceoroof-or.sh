#!/usr/bin/env bash
set -euo pipefail
python3 <<'PY'
from pathlib import Path
import json
for p in [Path("/docker/ceoroof/.env"), Path("/docker/ceoroof/secrets/openrouter.json")]:
    print(p, "exists" if p.exists() else "MISSING")
    if not p.exists():
        continue
    t = p.read_text(errors="ignore")
    if p.suffix == ".json":
        d = json.loads(t)
        for k, v in d.items():
            if "KEY" in k.upper() or k == "api_key":
                s = str(v)
                print(k, "len", len(s), "prefix", s[:10] + "...")
    else:
        for line in t.splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                print("OPENROUTER_API_KEY len", len(v), "prefix", v[:10] + "...")
            if line.startswith("OPENROUTER_FREE_MODEL=") or line.startswith("OPENROUTER_ESCALATION_MODEL=") or line.startswith("OPENROUTER_S1_MODEL="):
                print(line)
PY
echo "=== live hermes model/fallback ==="
docker exec -u root ceoroof-paperclip-1 python3 - <<'PY'
from pathlib import Path
t = Path("/paperclip/.hermes/config.yaml").read_text()
for line in t.splitlines():
    if line.startswith(("model", "fallback", "  ")) and (
        "provider" in line or "model" in line or "default" in line or line.startswith("model") or line.startswith("fallback")
    ):
        print(line)
PY
