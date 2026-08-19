#!/usr/bin/env bash
set +u
set -eo pipefail
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)

echo "=== index inject without query ==="
curl -sS http://127.0.0.1:9119/ | grep -o 'window.__HERMES_SESSION_TOKEN__="[^"]*"' | head -1
echo "=== index inject with query ==="
curl -sS "http://127.0.0.1:9119/?token=$TOKEN" | grep -o 'window.__HERMES_SESSION_TOKEN__="[^"]*"' | head -1

echo "=== read auth middleware loopback behavior ==="
python3 - <<'PY'
from pathlib import Path
p=Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py')
# may be in container only
PY
docker exec clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
p=Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py')
text=p.read_text()
# print relevant sections
for start in (340, 560, 2320, 12910, 12940):
    lines=text.splitlines()
    print(f"\n----- around {start} -----")
    for i in range(start-1, min(len(lines), start+40)):
        print(f"{i+1}:{lines[i]}")
PY

echo "=== gateway status now ==="
curl -sS http://127.0.0.1:9119/api/status | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("gateway_running"), d.get("active_sessions"), d.get("auth_required"))'
docker exec clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes gateway status 2>&1 | head -15'

echo "=== plugins public? ==="
curl -sS -o /dev/null -w "plugins:%{http_code}\n" http://127.0.0.1:9119/api/dashboard/plugins
curl -sS -o /dev/null -w "plugin_js:%{http_code}\n" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/dist/index.js || \
curl -sS -o /dev/null -w "assets_js:%{http_code}\n" http://127.0.0.1:9119/plugins/clawsum-cockpit/dist/index.js
# find how plugin entry is served
curl -sS http://127.0.0.1:9119/api/dashboard/plugins | python3 -c 'import sys,json; ps=json.load(sys.stdin);
for p in ps:
  if p["name"].startswith("clawsum"):
    print(p["name"], p.get("entry"), p.get("slots"))'
