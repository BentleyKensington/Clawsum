#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
ST=/tmp/clawsum-grafana-fix
cp -f "$ST/blackbox.yml" "$ROOT/blackbox.yml"
cp -f "$ST/prometheus.yml" "$ROOT/prometheus.yml"
# compose may live at ROOT
if [[ -f "$ST/docker-compose.yml" ]]; then
  cp -f "$ST/docker-compose.yml" "$ROOT/docker-compose.yml"
fi
sed -i 's/\r$//' "$ROOT/blackbox.yml" "$ROOT/prometheus.yml" "$ROOT/docker-compose.yml"
cd "$ROOT"
docker compose --profile monitoring up -d blackbox
sleep 2
curl -sS -X POST http://127.0.0.1:9090/-/reload >/dev/null
sleep 3
echo "=== probe boss with http_edge ==="
curl -sS "http://127.0.0.1:9115/probe?module=http_edge&target=https://boss.clawsum.com/" | grep -E '^probe_success|^probe_http_status'
echo "=== scrape wait + query ==="
sleep 35
curl -sS 'http://127.0.0.1:9090/api/v1/query?query=probe_success' | python3 -c '
import sys,json
d=json.load(sys.stdin)
for r in d.get("data",{}).get("result",[]):
  m=r.get("metric",{})
  if m.get("job") in ("clawsum-public","clawsum-health"):
    print(m.get("job"), m.get("service"), r.get("value")[1])
'
echo DONE
