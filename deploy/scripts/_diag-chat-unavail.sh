#!/usr/bin/env bash
set +u
set -eo pipefail
CONTAINER=clawsum-paperclip-1
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token 2>/dev/null || true)

echo "=== status ==="
curl -sS http://127.0.0.1:9119/api/status | python3 -m json.tool | head -40

echo "=== gateway ==="
docker exec "$CONTAINER" bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes gateway status 2>&1 | head -20'
docker exec "$CONTAINER" bash -lc 'ls -la /paperclip/logs/hermes-gateway.pid 2>/dev/null; tail -40 /paperclip/logs/hermes-gateway.log 2>/dev/null'

echo "=== recent gui/errors about unavailable/pty/ws ==="
docker exec "$CONTAINER" bash -lc '
  grep -iE "unavailable|pty refused|origin|4404|1006|embedded chat|tui|ws " /paperclip/.hermes/logs/gui.log 2>/dev/null | tail -40
  echo ---
  grep -iE "unavailable|pty|origin|ws |gateway" /paperclip/.hermes/logs/errors.log 2>/dev/null | tail -30
  echo ---
  tail -50 /paperclip/logs/hermes-dashboard.log 2>/dev/null
'

echo "=== ui-tui present? ==="
docker exec "$CONTAINER" bash -lc '
  ls -la /paperclip/.hermes-venv/lib/python3.13/site-packages/ui-tui 2>&1 | head
  ls -la /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist 2>&1 | head
  ls /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets 2>&1 | head
'

echo "=== chat unavailable string context ==="
docker exec "$CONTAINER" bash -lc '
  rg -n "Chat unavailable|embedded chat disabled|embedded terminal requires" \
    /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli -g "*.py" | head -30
'

echo "=== traefik origin rewrite ==="
grep -nE "Origin|hermes-host|boss.clawsum|9119" /docker/traefik/dynamic/clawsum-com.yml | head -40

echo "=== processes ==="
pgrep -af "hermes" | head -30 || true
