#!/usr/bin/env bash
set -euo pipefail
echo "=== blackbox listen ==="
ss -lntp | grep 9115 || netstat -lntp | grep 9115 || true
echo "=== prom can resolve/reach blackbox ==="
docker exec clawsum-prometheus-1 wget -qO- --timeout=3 http://host.docker.internal:9115/ 2>&1 | head -c 200 || true
echo
docker exec clawsum-prometheus-1 wget -qO- --timeout=3 http://172.17.0.1:9115/ 2>&1 | head -c 200 || true
echo
echo "=== prometheus.yml in container (health job) ==="
docker exec clawsum-prometheus-1 grep -A30 'clawsum-health' /etc/prometheus/prometheus.yml
echo "=== targets ==="
curl -sS http://127.0.0.1:9090/api/v1/targets > /tmp/t.json
python3 <<'PY'
import json
d=json.load(open("/tmp/t.json"))
for t in d.get("data",{}).get("activeTargets",[]):
  labels=t.get("labels") or {}
  print(f"health={t.get('health')} job={labels.get('job')} service={labels.get('service')} scrape={t.get('scrapeUrl')} err={(t.get('lastError') or '')[:140]}")
PY
echo "=== force reload + wait ==="
curl -sS -X POST http://127.0.0.1:9090/-/reload
sleep 40
curl -sS --get 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=probe_success' | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("count", len(d.get("data",{}).get("result",[])))
for r in d.get("data",{}).get("result",[]):
  m=r["metric"]; print(m.get("service"), r["value"][1], m.get("instance"))
'
