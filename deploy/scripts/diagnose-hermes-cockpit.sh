#!/usr/bin/env bash
# Diagnose why Clawsum tab/logo may not appear in Hermes UI.
set -euo pipefail
ENV=/docker/clawsum/.env
U=$(grep -E '^BOSS_OPS_AUTH_USER=' "$ENV" | cut -d= -f2- | tr -d '\r')
P=$(grep -E '^BOSS_OPS_AUTH_PASSWORD=' "$ENV" | cut -d= -f2- | tr -d '\r')
AUTH=(-u "${U}:${P}")

echo "=== dashboard process ==="
ps aux | grep -E '[h]ermes|[d]ashboard' | head -20 || true
ss -lntp | grep -E '9119|8787' || true

echo "=== hermes-dashboard.sh ==="
cat /docker/clawsum/scripts/hermes-dashboard.sh

echo "=== API probes (local) ==="
curl -sS -o /tmp/hstatus.json -w "status:%{http_code}\n" http://127.0.0.1:9119/api/status || true
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/tmp/hstatus.json')
if p.exists() and p.stat().st_size:
  d=json.loads(p.read_text())
  for k in sorted(d):
    if any(x in k.lower() for x in ('theme','plugin','auth','version','home','config')):
      print(f'{k}={d[k]}')
  print('keys', sorted(d.keys())[:40])
PY

echo "=== plugin routes ==="
for path in \
  /api/plugins \
  /api/plugins/clawsum-cockpit \
  /api/plugins/clawsum-cockpit/ \
  /api/plugins/clawsum-cockpit/health \
  /api/plugins/clawsum-cockpit/inbox \
  /api/plugins/clawsum-cockpit/assets/logo.png \
  /api/themes \
  /api/dashboard/themes
 do
  code=$(curl -sS -o /tmp/hp.json -w "%{http_code}" "http://127.0.0.1:9119${path}" || echo err)
  echo "$code $path"
  head -c 180 /tmp/hp.json 2>/dev/null; echo
done

echo "=== via traefik ==="
for path in /api/status /api/plugins/clawsum-cockpit/ /api/plugins/clawsum-cockpit/assets/logo.png; do
  code=$(curl -sk "${AUTH[@]}" -o /tmp/ht.json -w "%{http_code}" "https://hermes.clawsum.com${path}" || echo err)
  echo "$code https://hermes.clawsum.com${path}"
  head -c 120 /tmp/ht.json; echo
done

echo "=== hermes home env in paperclip ==="
docker exec clawsum-paperclip-1 bash -lc 'echo HERMES_HOME=${HERMES_HOME:-}; ls -la /root/.hermes 2>/dev/null | head; ls /paperclip/.hermes/plugins; which hermes; hermes --help 2>&1 | head -40'

echo "=== dashboard logs ==="
ls -lt /docker/clawsum/paperclip-data/.hermes/logs 2>/dev/null | head
tail -n 80 /docker/clawsum/paperclip-data/.hermes/logs/*.log 2>/dev/null | tail -80
docker exec clawsum-paperclip-1 bash -lc 'ls -lt /paperclip/.hermes/logs 2>/dev/null | head; tail -n 50 /paperclip/.hermes/logs/* 2>/dev/null | tail -60'
