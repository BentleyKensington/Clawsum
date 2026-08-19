#!/usr/bin/env bash
set -euo pipefail
CONTAINER=clawsum-paperclip-1
cp -f /tmp/hermes-dashboard.sh /docker/clawsum/scripts/hermes-dashboard.sh
chmod +x /docker/clawsum/scripts/hermes-dashboard.sh

docker exec -u root "$CONTAINER" bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin:$PATH
  export HERMES_HOME=/paperclip/.hermes
  mkdir -p /paperclip/logs
  echo "=== before ==="
  hermes gateway status 2>&1 | sed -n "1,15p"
  if hermes gateway status 2>&1 | grep -qi running; then
    echo gateway_already
  else
    nohup hermes gateway run --accept-hooks >>/paperclip/logs/hermes-gateway.log 2>&1 &
    echo $! > /paperclip/logs/hermes-gateway.pid
    echo started_gateway pid=$(cat /paperclip/logs/hermes-gateway.pid)
    sleep 4
  fi
  echo "=== after ==="
  hermes gateway status 2>&1 | sed -n "1,20p"
  echo "=== log ==="
  tail -n 25 /paperclip/logs/hermes-gateway.log 2>/dev/null || true
'
python3 - <<'PY'
import json, urllib.request
d = json.load(urllib.request.urlopen("http://127.0.0.1:9119/api/status"))
keys = ("gateway_running", "gateway_state", "active_sessions", "gateway_pid", "gateway_platforms")
print({k: d.get(k) for k in keys})
PY
