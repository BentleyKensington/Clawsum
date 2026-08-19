#!/usr/bin/env bash
set -euo pipefail
python3 <<'PY'
from pathlib import Path
import json
roots = [
    Path("/docker/clawsum"),
    Path("/docker/clawsum/secrets"),
    Path("/docker/clawsum/paperclip-data"),
    Path("/docker/clawsum/paperclip-data/.hermes"),
]
# list secrets dirs
for p in [Path("/docker/clawsum/secrets"), Path("/docker/clawsum/paperclip-data/secrets"), Path("/root/secrets")]:
    print("DIR", p, "exists" if p.exists() else "MISSING")
    if p.exists():
        for c in sorted(p.iterdir()):
            print(" ", c.name, c.stat().st_size)

# find openrouter-ish files
hits = []
for root in roots:
    if not root.exists():
        continue
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if "openrouter" in name or name in {"secrets.json", "llm.json", "api-keys.json"}:
            hits.append(p)
print("HITS", len(hits))
for p in hits[:40]:
    print(p)
    try:
        t = p.read_text(errors="ignore")
    except Exception as e:
        print("  read_err", e)
        continue
    if p.suffix == ".json":
        try:
            d = json.loads(t)
            if isinstance(d, dict):
                for k, v in d.items():
                    if "KEY" in str(k).upper() or "openrouter" in str(k).lower() or k == "api_key":
                        s = str(v)
                        print(f"  {k} len={len(s)} prefix={s[:8]}...")
        except Exception as e:
            print("  json_err", e)
    else:
        for line in t.splitlines():
            if "OPENROUTER" in line and "=" in line:
                k, _, v = line.partition("=")
                vv = v.strip().strip('"').strip("'")
                print(f"  {k.strip()} len={len(vv)} prefix={vv[:8]}...")

# .env current OR key fingerprint only
env = Path("/docker/clawsum/.env")
if env.exists():
    for line in env.read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            v = line.split("=",1)[1].strip().strip('"').strip("'")
            print("ENV_OPENROUTER len", len(v), "prefix", v[:10]+"...", "suffix", "..."+v[-6:])
PY
# compare to what we just wrote in hermes .env
docker exec -u root clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
p=Path("/paperclip/.hermes/.env")
print("HERMES_ENV", p.exists())
if p.exists():
  for line in p.read_text().splitlines():
    if line.startswith("OPENROUTER_API_KEY="):
      v=line.split("=",1)[1]
      print("hermes_or len", len(v), "prefix", v[:10]+"...", "suffix", "..."+v[-6:])
print("--- config ---")
print(Path("/paperclip/.hermes/config.yaml").read_text()[:600])
PY
