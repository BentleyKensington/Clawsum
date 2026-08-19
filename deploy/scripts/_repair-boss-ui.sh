#!/usr/bin/env bash
set +u
set -eo pipefail
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
CONTAINER=clawsum-paperclip-1

echo "=== plugin asset paths with token ==="
# Discover actual plugin asset URL pattern from web_server
docker exec "$CONTAINER" python3 - <<'PY'
from pathlib import Path
import re
t=Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py').read_text()
for m in re.finditer(r'.{0,80}plugins/.{0,120}', t):
    s=m.group(0)
    if 'dist' in s or 'static' in s or 'entry' in s:
        print(s[:200])
PY

for url in \
  "/api/plugins/clawsum-cockpit/assets/dist/index.js" \
  "/plugins/clawsum-cockpit/dist/index.js" \
  "/api/plugins/clawsum-cockpit/files/dist/index.js" \
  "/plugin-assets/clawsum-cockpit/dist/index.js"
 do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -H "X-Hermes-Session-Token: $TOKEN" "http://127.0.0.1:9119$url" || echo err)
  echo "$code $url"
done

# grep web for plugin file route
docker exec "$CONTAINER" rg -n "plugin.*dist|serve.*plugin|/plugins/\{" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py | head -40

echo "=== ensure no-cache on HTML via traefik + start gateway with dashboard ==="
# patch clawsum-com.yml to add cache-control for hermes if missing
python3 - <<'PY'
from pathlib import Path
p=Path('/docker/traefik/dynamic/clawsum-com.yml')
t=p.read_text()
changed=False
if 'hermes-nocache' not in t:
    # insert middleware definition near hermes-host-rewrite
    needle='    hermes-host-rewrite:'
    block='''    hermes-nocache:
      headers:
        customResponseHeaders:
          Cache-Control: "no-store, no-cache, must-revalidate"
          Pragma: "no-cache"
    hermes-host-rewrite:'''
    if needle in t:
        t=t.replace(needle, block, 1)
        changed=True
        print('added hermes-nocache middleware')
    else:
        print('hermes-host-rewrite not found')
# add middleware to routers that use hermes-host-rewrite
import re
def add_mw(text, router_key):
    # find router block and middlewares list
    m=re.search(rf'(  {re.escape(router_key)}:\n(?:    .*\n)*?    middlewares:\n)((?:      - .*\n)+)', text)
    if not m:
        print('router', router_key, 'not found or no middlewares')
        return text, False
    block=m.group(0)
    if 'hermes-nocache' in block:
        print(router_key, 'already has nocache')
        return text, False
    insert=m.group(1)+'      - hermes-nocache\n'+m.group(2)
    return text.replace(block, insert, 1), True

for r in ('clawsum-hermes', 'clawsum-boss', 'boss', 'hermes'):
    t2, c = add_mw(t, r)
    if c:
        t=t2; changed=True; print('wired', r)

if changed:
    p.write_text(t)
    print('wrote', p)
else:
    print('no traefik changes needed or partial')
# show hermes/boss router snippets
for line_no, line in enumerate(t.splitlines(),1):
    if 'hermes' in line.lower() or 'boss' in line.lower() or 'nocache' in line or 'Origin' in line:
        if any(x in line for x in ('clawsum-', 'hermes-', 'boss', 'Origin', 'nocache', 'middlewares', 'rule:')):
            print(f'{line_no}:{line}')
PY

echo "=== rewrite hermes-dashboard.sh to also ensure gateway ==="
# Create companion start script
cat > /docker/clawsum/scripts/ensure-hermes-runtime.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
bash /docker/clawsum/scripts/hermes-dashboard.sh status || bash /docker/clawsum/scripts/hermes-dashboard.sh start
# gateway
docker exec -u root "$CONTAINER" bash -lc '
  set +e
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  export HERMES_HOME=/paperclip/.hermes
  mkdir -p /paperclip/logs
  if hermes gateway status 2>&1 | grep -q "✓ Gateway is running"; then
    echo gateway_ok
    exit 0
  fi
  nohup hermes gateway run --accept-hooks >>/paperclip/logs/hermes-gateway.log 2>&1 &
  echo $! > /paperclip/logs/hermes-gateway.pid
  sleep 2
  hermes gateway status 2>&1 | head -5
'
# verify APIs with token
TOKEN=$(tr -d "\r\n" < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
curl -sf -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/health >/dev/null \
  && echo cockpit_api_ok || echo cockpit_api_FAIL
curl -sS http://127.0.0.1:9119/api/status | python3 -c "import sys,json;d=json.load(sys.stdin);print('gateway_running',d.get('gateway_running'))"
EOF
chmod +x /docker/clawsum/scripts/ensure-hermes-runtime.sh
bash /docker/clawsum/scripts/ensure-hermes-runtime.sh

echo "=== reinstall sidebar plugins (full) ==="
bash /docker/clawsum/scripts/install-clawsum-sidebar-plugins.sh
bash /docker/clawsum/scripts/force-restart-hermes-dashboard.sh
sleep 2
bash /docker/clawsum/scripts/ensure-hermes-runtime.sh

echo "=== final verify ==="
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
curl -sS -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-briefs?limit=2 | python3 -c 'import sys,json;d=json.load(sys.stdin);print("briefs",d.get("count"), d.get("ok"), (d.get("briefs") or [{}])[0].get("greeting"))'
curl -sS -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/archive | python3 -c 'import sys,json;d=json.load(sys.stdin);print("archive ok",d.get("ok"),"session_briefs",d.get("session_briefs_count"), "err",d.get("error"))'
curl -sS http://127.0.0.1:9119/api/status | python3 -c 'import sys,json;d=json.load(sys.stdin);print({k:d.get(k) for k in ("gateway_running","auth_required","active_sessions","version")})'
