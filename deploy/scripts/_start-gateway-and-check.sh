#!/usr/bin/env bash
set +u
set -eo pipefail
CONTAINER=clawsum-paperclip-1

echo "=== start gateway for real ==="
docker exec -u root "$CONTAINER" bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  export HERMES_HOME=/paperclip/.hermes
  mkdir -p /paperclip/logs
  # kill stale
  if [[ -f /paperclip/logs/hermes-gateway.pid ]]; then
    kill $(cat /paperclip/logs/hermes-gateway.pid) 2>/dev/null || true
    rm -f /paperclip/logs/hermes-gateway.pid
  fi
  nohup hermes gateway run --accept-hooks >>/paperclip/logs/hermes-gateway.log 2>&1 &
  echo $! > /paperclip/logs/hermes-gateway.pid
  echo started_pid=$(cat /paperclip/logs/hermes-gateway.pid)
'
sleep 5
docker exec "$CONTAINER" bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes gateway status 2>&1 | head -30'
echo "--- gateway log ---"
docker exec "$CONTAINER" tail -40 /paperclip/logs/hermes-gateway.log || true
curl -sS http://127.0.0.1:9119/api/status | python3 -c 'import sys,json; d=json.load(sys.stdin); print("gateway_running",d.get("gateway_running"),"platforms",d.get("gateway_platforms"),"active_sessions",d.get("active_sessions"))'

echo "=== traefik boss/hermes origin ==="
grep -nE 'boss|hermes|Origin|9119|clawsum-hermes|clawsum-boss' /docker/traefik/dynamic/clawsum-com.yml | head -80

echo "=== unavailable strings in UI assets ==="
docker exec "$CONTAINER" bash -lc '
  find /paperclip/.hermes-venv -type d -name "ui*" 2>/dev/null | head
  find /paperclip/.hermes-venv -type f \( -name "*.js" -o -name "*.mjs" \) 2>/dev/null | head -30
  rg -n -i "unavailable|Gateway is not|gateway_running|Chat.*offline" /paperclip/.hermes-venv/lib/python3.13/site-packages --glob "*.js" -g "!**/node_modules/**" 2>/dev/null | head -40 || \
  grep -Rsn --include="*.js" -i "unavailable" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes* 2>/dev/null | head -40
'
