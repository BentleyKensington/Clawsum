#!/usr/bin/env bash
set -euo pipefail
curl -sS "http://127.0.0.1:9090/api/v1/targets" > /tmp/prom-targets.json
python3 <<'PY'
import json
d=json.load(open("/tmp/prom-targets.json"))
ts=d.get("data",{}).get("activeTargets",[])
print("targets", len(ts))
for t in sorted(ts, key=lambda x: (x.get("labels",{}).get("job",""), x.get("labels",{}).get("instance",""))):
    labels=t.get("labels") or {}
    job=labels.get("job","")
    inst=labels.get("instance","")
    svc=labels.get("service","")
    health=t.get("health")
    err=(t.get("lastError") or "")[:160]
    print(f"{health:6} job={job:22} svc={svc:20} inst={inst} err={err}")
PY
echo "=== blackbox self ==="
curl -sS -o /dev/null -w "blackbox_metrics %{http_code}\n" http://127.0.0.1:9115/metrics || echo blackbox_down
echo "=== probe boss ==="
curl -sS "http://127.0.0.1:9115/probe?module=http_2xx&target=https://boss.clawsum.com/" | grep -E '^probe_success|^probe_http_status_code|^probe_duration_seconds ' || true
echo "=== probe local hermes ==="
curl -sS "http://127.0.0.1:9115/probe?module=http_2xx&target=http://127.0.0.1:9119/" | grep -E '^probe_success|^probe_http_status_code' || true
echo "=== from prometheus container ==="
docker exec clawsum-prometheus-1 wget -qO- "http://host.docker.internal:9115/probe?module=http_2xx&target=https://boss.clawsum.com/" 2>&1 | head -5 || \
docker exec clawsum-prometheus-1 wget -qO- "http://172.17.0.1:9115/probe?module=http_2xx&target=https://boss.clawsum.com/" 2>&1 | head -5 || true
echo "=== query probe_success ==="
curl -sS 'http://127.0.0.1:9090/api/v1/query?query=probe_success' | python3 -c 'import sys,json; d=json.load(sys.stdin); 
for r in d.get("data",{}).get("result",[]):
  m=r.get("metric",{}); print(m.get("job"), m.get("service"), m.get("instance"), r.get("value"))'
echo "=== uptime avg ==="
curl -sS --get 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=avg_over_time(probe_success[1h])' | python3 -c 'import sys,json; d=json.load(sys.stdin);
for r in d.get("data",{}).get("result",[])[:20]:
  m=r.get("metric",{}); print(m.get("job"), m.get("service") or m.get("instance"), r.get("value"))'
