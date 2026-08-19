#!/usr/bin/env bash
# Diagnose CLA-59 / Avenou Paperclip host routing + issue state
set -euo pipefail
ROOT=/docker/clawsum
ENVF="$ROOT/.env"

echo "=== listening ports 3100/3101/48166 ==="
ss -lntp 2>/dev/null | grep -E ':(3100|3101|48166)\b' || netstat -lntp 2>/dev/null | grep -E ':(3100|3101|48166)\b' || true

echo "=== .env PAPERCLIP / BOSS (redacted) ==="
grep -E '^(PAPERCLIP|CLAWSUM_BOSS|OPENCLAW|GHL_AVE|GHL_.*AVE)' "$ENVF" 2>/dev/null | sed -E 's/(TOKEN|SECRET|KEY|PASSWORD|PIT|JWT)=.*/\1=SET/' || true

echo "=== docker paperclip / gateway ==="
docker ps --format '{{.Names}} {{.Ports}} {{.Status}}' | grep -Ei 'paperclip|openclaw|hermes' || true

echo "=== ghl-accounts.json avenou ==="
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/docker/clawsum/config/ghl-accounts.json")
if not p.exists():
    print("missing", p)
else:
    cfg = json.loads(p.read_text())
    for a in cfg.get("accounts", []):
        if "ave" in a.get("id","").lower() or "avenou" in json.dumps(a).lower():
            print(json.dumps({k:a.get(k) for k in ("id","slug","display_name","paperclip_name","schema_prefix") if k in a or True}, indent=2))
    print("all ids:", [a.get("id") for a in cfg.get("accounts", [])])
PY

echo "=== openclaw agent list (ids) ==="
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
cfg = json.loads(p.read_text())
for a in cfg.get("agents", {}).get("list", []):
    print(a.get("id"), a.get("name"), a.get("workspace"))
PY

echo "=== paperclip config adapter snippets ==="
python3 - <<'PY'
import json
from pathlib import Path
cands = [
    Path("/docker/clawsum/paperclip-data/instances/default/config.json"),
    Path("/docker/clawsum/paperclip-data/config.json"),
]
for p in cands:
    if p.exists():
        print("found", p)
        try:
            cfg = json.loads(p.read_text())
            print("keys", list(cfg.keys())[:30])
        except Exception as e:
            print("parse fail", e)
PY

echo "=== probe APIs ==="
for port in 3100 3101; do
  code=$(curl -sS -m 3 -o /tmp/pc-health-$port.json -w '%{http_code}' "http://127.0.0.1:$port/api/health" || echo fail)
  echo "port $port health => $code"
  head -c 200 /tmp/pc-health-$port.json 2>/dev/null; echo
done

echo "=== CLA-59 lookup via 3100 ==="
python3 - <<'PY'
import json, os, urllib.request, urllib.error
from pathlib import Path

env = {}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    line=line.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    k,_,v=line.partition("=")
    env[k.strip()]=v.strip().strip('"').strip("'")

cid = env.get("PAPERCLIP_COMPANY_ID") or env.get("PAPERCLIP_COMPANY") or ""
api = env.get("PAPERCLIP_API") or "http://127.0.0.1:3100/api"
print("API", api, "company", cid)

def get(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except Exception as e:
        return 0, str(e)

# list agents
if cid:
    code, agents = get(f"{api.rstrip('/')}/companies/{cid}/agents")
    print("agents", code)
    if isinstance(agents, list):
        for a in agents:
            name=a.get("name","")
            if "ave" in name.lower() or "avenou" in name.lower() or "ghl" in name.lower() or "hermes" in name.lower() or "media" in name.lower():
                cfg=a.get("adapterConfig") or a.get("config") or {}
                print("-", name, "id=", a.get("id"), "adapter=", a.get("adapterType"), "url hints=", json.dumps(cfg)[:400])

# search issues
for q in ("CLA-59", "Avenou", "avenou", "index"):
    code, body = get(f"{api.rstrip('/')}/companies/{cid}/issues?q={q}" if cid else "")
    if not cid:
        break
    print("search", q, code, type(body).__name__)
    items = body if isinstance(body, list) else (body.get("issues") or body.get("items") or []) if isinstance(body, dict) else []
    for it in (items or [])[:8]:
        print(" ", it.get("identifier") or it.get("number"), it.get("status"), (it.get("title") or "")[:80], "assignee", (it.get("assignee") or {}).get("name") if isinstance(it.get("assignee"), dict) else it.get("assigneeId"))

# try identifier path
for path in (
    f"{api.rstrip('/')}/companies/{cid}/issues?identifier=CLA-59",
    f"{api.rstrip('/')}/issues/CLA-59",
):
    if not cid and "companies" in path:
        continue
    code, body = get(path)
    print("path", path, "=>", code, str(body)[:300])
PY

echo "=== workspace-ghl-ave TOOLS/SOUL paperclip urls ==="
for d in /docker/clawsum/data/.openclaw/workspace-ghl-ave-rei /docker/clawsum/data/.openclaw/workspace-*; do
  [ -d "$d" ] || continue
  base=$(basename "$d")
  if echo "$base" | grep -qiE 'ave|avenou|ghl'; then
    echo "-- $base --"
    grep -RIn -E 'paperclip\.clawsum|3100|3101|PAPERCLIP' "$d" 2>/dev/null | head -40 || true
  fi
done

echo "=== DONE ==="
