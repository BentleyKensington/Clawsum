#!/usr/bin/env bash
set -euo pipefail
echo "=== OpenRouter key presence ==="
python3 - <<'PY'
from pathlib import Path
for p in [Path("/docker/clawsum/.env"), Path("/docker/clawsum/secrets/openrouter.json")]:
    print(p, "exists" if p.exists() else "MISSING")
    if not p.exists():
        continue
    t = p.read_text(errors="ignore")
    if p.suffix == ".json":
        print("  has_OPENROUTER", "OPENROUTER" in t or "api_key" in t)
    else:
        for line in t.splitlines():
            if line.startswith("OPENROUTER") or line.startswith("ANTHROPIC") or line.startswith("OPENAI_API"):
                k = line.split("=",1)[0]
                v = line.split("=",1)[1] if "=" in line else ""
                print(f"  {k}=len={len(v.strip().strip(chr(34)).strip(chr(39)))}")
PY
echo "=== current hermes config model ==="
docker exec -u root clawsum-paperclip-1 python3 -c 'from pathlib import Path; print(Path("/paperclip/.hermes/config.yaml").read_text())'
