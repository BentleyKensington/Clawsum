#!/usr/bin/env bash
set +u
set -eo pipefail
CONTAINER=clawsum-paperclip-1
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)

echo "=== how SPA gets token ==="
docker exec "$CONTAINER" bash -lc '
  python3 - <<"PY"
from pathlib import Path
html = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/index.html").read_text()
for needle in ("SESSION_TOKEN", "session_token", "auth_required", "__HERMES", "token"):
    if needle.lower() in html.lower():
        print("html has", needle)
print(html[:1500])
PY
'

echo "=== search web_server for auth_required / session token ==="
docker exec "$CONTAINER" bash -lc '
  rg -n "auth_required|HERMES_DASHBOARD_SESSION|session.token|X-Hermes-Session" \
    /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli --glob "*.py" | head -60
'

echo "=== bootstrap endpoints ==="
for p in /api/auth/status /api/session /api/bootstrap /api/config /api/dashboard/session; do
  code=$(curl -sS -o /tmp/b.json -w "%{http_code}" "http://127.0.0.1:9119$p" || echo err)
  echo "$code $p"; head -c 200 /tmp/b.json; echo
done

echo "=== with token query ==="
curl -sS -o /tmp/h.html -w "html:%{http_code}\n" "http://127.0.0.1:9119/?token=$TOKEN" || true
grep -oE '__HERMES_SESSION_TOKEN__[^<]{0,80}|session.token[^<]{0,80}|token=[A-Za-z0-9_-]{10,}' /tmp/h.html | head

echo "=== traefik inject token? ==="
grep -nE 'token|SESSION|Authorization|ForwardAuth' /docker/traefik/dynamic/clawsum-com.yml | head -40
