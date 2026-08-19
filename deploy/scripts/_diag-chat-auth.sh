#!/usr/bin/env bash
set +u
set -eo pipefail
echo "=== api/status full gateway fields ==="
curl -sS http://127.0.0.1:9119/api/status | python3 -m json.tool | head -80

echo "=== with session token ==="
TOKEN=$(docker exec clawsum-paperclip-1 tr -d '\r\n' < /paperclip/.hermes/dashboard-session.token)
echo "token_len=${#TOKEN}"
for p in health archive session-briefs authority; do
  code=$(curl -sS -o /tmp/cp.json -w "%{http_code}" \
    -H "X-Hermes-Session-Token: $TOKEN" \
    "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/$p" || echo err)
  echo "$code $p"
  head -c 280 /tmp/cp.json; echo
done

echo "=== find unavailable string in hermes package ==="
docker exec clawsum-paperclip-1 bash -lc 'grep -Rsn --include="*.js" --include="*.tsx" --include="*.ts" --include="*.jsx" -i "unavailable\|gateway_running\|Chat unavailable\|Gateway offline" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web* 2>/dev/null | head -40; find /paperclip/.hermes-venv -name "*.js" 2>/dev/null | head; ls /paperclip/.hermes-venv/lib/python3.13/site-packages/ | grep -i hermes | head'

echo "=== processes on host ==="
pgrep -af 'hermes|dashboard|gateway' | head -40 || true

echo "=== traefik boss vs hermes ==="
grep -nE 'boss\.clawsum|hermes\.clawsum|9119' /docker/traefik/dynamic/*.yml 2>/dev/null | head -40
