#!/usr/bin/env bash
# Fix Clawsum sidebar: inbox DB access, Skill map tab, contrast, redeploy plugins.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${ROOT}/examples/hermes-cockpit"
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
H=/paperclip/.hermes
HOST_H="${ROOT}/paperclip-data/.hermes"

echo "== write clawsum-runtime.env (postgres for Hermes plugins) =="
python3 - <<PY
from pathlib import Path
env = {}
for line in Path("${ROOT}/.env").read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")
keys = [
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "GMAIL_ADMIN_ADDRESS", "CLAWSUM_BOSS_URL", "CLAWSUM_OPENCLAW_URL", "CLAWSUM_GRAFANA_URL",
    "CLAWSUM_GRAFANA_EMBED_URL", "CLAWSUM_HERMES_URL", "PAPERCLIP_API", "PAPERCLIP_COMPANY_ID",
]
lines = ["# generated for Hermes cockpit plugins — do not commit"]
for k in keys:
    if k == "POSTGRES_HOST":
        lines.append(f"{k}={env.get(k) or '127.0.0.1'}")
    elif k == "POSTGRES_PORT":
        lines.append(f"{k}={env.get(k) or '5432'}")
    elif env.get(k):
        lines.append(f"{k}={env[k]}")
out = Path("${HOST_H}/clawsum-runtime.env")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print("wrote", out, "bytes", out.stat().st_size)
PY
# also next to plugin_api
mkdir -p "${HOST_H}/plugins/clawsum-cockpit/dashboard"
cp -f "${HOST_H}/clawsum-runtime.env" \
  "${HOST_H}/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env" 2>/dev/null || true

echo "== install psycopg2 into Hermes venv =="
docker exec -u root "${CONTAINER}" bash -lc '
set -e
export PATH=/paperclip/.hermes-venv/bin:$PATH
pip install -q --disable-pip-version-check psycopg2-binary
python3 -c "import psycopg2; print(\"psycopg2\", psycopg2.__version__)"
'

echo "== sync examples from this host tree if present =="
# Prefer /docker/clawsum/examples (flat) — may already be updated via scp

echo "== rebuild + install sidebar plugins =="
bash "${ROOT}/scripts/install-clawsum-sidebar-plugins.sh"

echo "== verify inbox API =="
TOKEN=$(cat "${HOST_H}/dashboard-session.token")
curl -sS -o /tmp/inbox-fix.json -w "inbox:%{http_code}\n" \
  -H "Authorization: Bearer ${TOKEN}" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/inbox
python3 - <<'PY'
import json
from pathlib import Path
d=json.loads(Path("/tmp/inbox-fix.json").read_text())
print("ok", d.get("ok"), "items", len(d.get("action_items") or []), "analyses", len(d.get("email_analyses") or []), "error", d.get("error"))
if not d.get("ok"):
  raise SystemExit("inbox still broken")
PY
curl -sS -H "Authorization: Bearer ${TOKEN}" http://127.0.0.1:9119/api/dashboard/plugins \
  | python3 -c "import sys,json; print([(p['name'],p.get('label'), (p.get('tab') or {}).get('path')) for p in json.load(sys.stdin)])"
echo DONE
