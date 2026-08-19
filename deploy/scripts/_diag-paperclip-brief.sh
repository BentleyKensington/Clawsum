#!/usr/bin/env bash
set +u
set -eo pipefail
ROOT=/docker/clawsum
CONTAINER=clawsum-paperclip-1

echo "=== env keys (redacted) ==="
grep -E '^(PAPERCLIP_|CLAWSUM_BOSS)' "$ROOT/.env" | sed -E 's/(PASSWORD|TOKEN|SECRET|KEY)=.*/\1=***/' || true

echo "=== runtime env for hermes plugins ==="
docker exec "$CONTAINER" bash -lc '
  for f in /paperclip/.hermes/clawsum-runtime.env \
           /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env; do
    echo "-- $f"
    if [[ -f $f ]]; then
      grep -E "^(PAPERCLIP_|POSTGRES_|CLAWSUM_)" "$f" | sed -E "s/(PASSWORD|TOKEN|SECRET|KEY)=.*/\1=***/"
    else
      echo MISSING
    fi
  done
'

echo "=== paperclip containers / ports ==="
docker ps --format '{{.Names}} {{.Ports}}' | grep -iE 'paperclip|3100' || true
ss -lntp 2>/dev/null | grep -E '3100|9119' || netstat -lntp 2>/dev/null | grep -E '3100|9119' || true

echo "=== probe paperclip from host ==="
curl -sS -o /tmp/pc.json -w "host:%{http_code}\n" http://127.0.0.1:3100/api/health 2>/dev/null || echo host_fail
head -c 200 /tmp/pc.json; echo
curl -sS -o /tmp/pc2.json -w "host_companies:%{http_code}\n" http://127.0.0.1:3100/api/companies 2>/dev/null || true
head -c 300 /tmp/pc2.json; echo

echo "=== probe from paperclip container ==="
docker exec "$CONTAINER" bash -lc '
  curl -sS -o /tmp/pc.json -w "loop:%{http_code}\n" http://127.0.0.1:3100/api/health || echo loop_fail
  head -c 200 /tmp/pc.json; echo
  # try docker DNS names
  for u in http://127.0.0.1:3100/api/health http://clawsum-paperclip-1:3100/api/health http://paperclip:3100/api/health; do
    code=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 2 "$u" || echo err)
    echo "$code $u"
  done
'

echo "=== brief API ==="
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token")
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/brief | python3 -m json.tool | head -60
