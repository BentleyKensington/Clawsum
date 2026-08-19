#!/usr/bin/env bash
set +u
set -eo pipefail
ROOT=/docker/clawsum
CONTAINER=clawsum-paperclip-1
HOST_H="$ROOT/paperclip-data/.hermes"

# Discover company id
COMPANY=$(curl -sS http://127.0.0.1:3100/api/companies | python3 -c '
import sys,json
rows=json.load(sys.stdin)
pref=None
for r in rows:
  if (r.get("name") or "").lower()=="clawsum":
    pref=r["id"]; break
print(pref or (rows[0]["id"] if rows else ""))
')
echo "COMPANY=$COMPANY"
test -n "$COMPANY"

# Probe dashboard endpoint
curl -sS -o /tmp/pcdash.json -w "dash:%{http_code}\n" \
  "http://127.0.0.1:3100/api/companies/${COMPANY}/dashboard" || true
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/tmp/pcdash.json')
if not p.exists() or not p.stat().st_size:
  print('empty dashboard response')
else:
  d=json.loads(p.read_text())
  print('keys', sorted(d.keys())[:30] if isinstance(d, dict) else type(d))
  if isinstance(d, dict):
    for k in ('agents','agentCounts','tasks','issueCounts','issues','openIssues'):
      if k in d: print(k, d[k])
PY

# Ensure .env has PAPERCLIP_API + COMPANY_ID (append if missing)
python3 - <<PY
from pathlib import Path
env_path = Path("$ROOT/.env")
text = env_path.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()
keys = {}
order = []
for line in lines:
    if not line.strip() or line.strip().startswith("#") or "=" not in line:
        order.append(("raw", line))
        continue
    k, _, v = line.partition("=")
    k = k.strip()
    keys[k] = v
    order.append(("kv", k))

updates = {
    "PAPERCLIP_API": "http://127.0.0.1:3100/api",
    "PAPERCLIP_COMPANY_ID": "$COMPANY",
}
changed = False
for k, v in updates.items():
    if keys.get(k) != v:
        keys[k] = v
        changed = True
        print(f"set {k}")
if changed:
    out = []
    seen = set()
    for kind, val in order:
        if kind == "raw":
            out.append(val)
        else:
            if val in seen:
                continue
            seen.add(val)
            if val in updates:
                out.append(f"{val}={keys[val]}")
            else:
                out.append(f"{val}={keys[val]}")
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    env_path.write_text("\\n".join(out) + "\\n", encoding="utf-8")
    print("wrote", env_path)
else:
    print(".env already has correct Paperclip keys")
PY

# Rebuild clawsum-runtime.env including Paperclip keys
python3 - <<PY
from pathlib import Path
env = {}
for line in Path("$ROOT/.env").read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")
keys = [
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "GMAIL_ADMIN_ADDRESS", "CLAWSUM_BOSS_URL", "CLAWSUM_OPENCLAW_URL", "CLAWSUM_GRAFANA_URL",
    "CLAWSUM_GRAFANA_EMBED_URL", "CLAWSUM_HERMES_URL", "PAPERCLIP_API", "PAPERCLIP_COMPANY_ID",
    "PAPERCLIP_PUBLIC_URL",
]
lines = ["# generated for Hermes cockpit plugins — do not commit"]
for k in keys:
    if k == "POSTGRES_HOST":
        lines.append(f"{k}={env.get(k) or '127.0.0.1'}")
    elif k == "POSTGRES_PORT":
        lines.append(f"{k}={env.get(k) or '5432'}")
    elif k == "PAPERCLIP_API":
        lines.append(f"{k}={env.get(k) or 'http://127.0.0.1:3100/api'}")
    elif env.get(k):
        lines.append(f"{k}={env[k]}")
out = Path("$HOST_H/clawsum-runtime.env")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print("wrote", out)
print(out.read_text())
PY

docker cp "$HOST_H/clawsum-runtime.env" "$CONTAINER:/paperclip/.hermes/clawsum-runtime.env"
docker exec -u root "$CONTAINER" mkdir -p /paperclip/.hermes/plugins/clawsum-cockpit/dashboard
docker cp "$HOST_H/clawsum-runtime.env" \
  "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env"

# Plugin caches runtime env in-process — restart dashboard to pick up
bash "$ROOT/scripts/force-restart-hermes-dashboard.sh" || bash "$ROOT/scripts/hermes-dashboard.sh start"
sleep 2
bash "$ROOT/scripts/ensure-hermes-runtime.sh" || true

TOKEN=$(tr -d '\r\n' < "$HOST_H/dashboard-session.token")
echo "=== brief after fix ==="
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/brief | python3 -m json.tool | head -80

echo "=== session-startup report ==="
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-startup \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("report")); print("pending",d.get("pending_approvals"),"archive",d.get("archive_pending"))'
echo DONE
