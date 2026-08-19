#!/usr/bin/env bash
set -euo pipefail
python3 <<'PY'
from pathlib import Path
import json
paths = [
    Path("/docker/ceoroof/.env"),
    Path("/docker/ceoroof/secrets/openrouter.json"),
    Path("/docker/clawsum/.env"),
    Path("/docker/clawsum/secrets/openrouter.json"),
]
for p in paths:
    print("---", p, "exists" if p.exists() else "MISSING")
    if not p.exists():
        continue
    t = p.read_text(errors="ignore")
    if p.suffix == ".json":
        try:
            d = json.loads(t)
        except Exception as e:
            print("json_err", e)
            continue
        for k, v in d.items():
            if "KEY" in k.upper() or k == "api_key":
                print(k, "len", len(str(v)))
    else:
        for line in t.splitlines():
            if "OPENROUTER" in line and "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                vv = v.strip().strip('"').strip("'")
                print(k.strip(), "len", len(vv))
PY
echo "=== ceoroof hermes live model? ==="
if docker ps --format '{{.Names}}' | grep -q ceoroof-paperclip; then
  docker exec -u root ceoroof-paperclip-1 python3 -c 'from pathlib import Path; print(Path("/paperclip/.hermes/config.yaml").read_text()[:800])' 2>/dev/null || true
  docker exec -u root -e HERMES_HOME=/paperclip/.hermes -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin ceoroof-paperclip-1 hermes auth list 2>&1 | sed -n '1,40p' || true
else
  echo "no ceoroof-paperclip container"
fi
ls -la /docker/ceoroof/secrets/ 2>/dev/null | sed -n '1,30p' || echo no_ceoroof_secrets
ls -la /docker/clawsum/secrets/ 2>/dev/null | sed -n '1,30p' || echo no_clawsum_secrets
