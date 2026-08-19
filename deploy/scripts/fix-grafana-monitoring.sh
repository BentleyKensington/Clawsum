#!/usr/bin/env bash
# Fix Grafana provisioning perms, reload Prometheus + Grafana monitoring stack.
set -euo pipefail
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
cd "$CLAWSUM_DIR"

mkdir -p data/prometheus data/grafana \
  grafana/provisioning/datasources \
  grafana/provisioning/dashboards/json \
  prometheus/alerts

# Grafana runs as uid 472 — provisioning was root-only and datasource never loaded
chown -R 472:472 data/grafana grafana
chmod -R u+rwX,go+rX grafana
chown -R 65534:65534 data/prometheus

docker compose --profile monitoring up -d blackbox prometheus grafana
sleep 4

# Hot-reload Prometheus config if already running
curl -sS -X POST http://127.0.0.1:9090/-/reload >/dev/null 2>&1 || true
sleep 2

echo "== prometheus =="
curl -sS -o /dev/null -w "healthy=%{http_code}\n" http://127.0.0.1:9090/-/healthy
python3 - <<'PY'
import json, urllib.request
d = json.load(urllib.request.urlopen("http://127.0.0.1:9090/api/v1/targets", timeout=10))
ts = d.get("data", {}).get("activeTargets", [])
print(f"targets={len(ts)}")
for t in ts:
    labels = t.get("labels") or {}
    err = (t.get("lastError") or "")[:80]
    print(f"  {t.get('health')} job={labels.get('job')} service={labels.get('service','')} instance={labels.get('instance')} {err}")
PY

echo "== grafana =="
curl -sS -o /dev/null -w "health=%{http_code}\n" http://127.0.0.1:3000/api/health
curl -sS -o /tmp/gf-ds.json -w "datasources_http=%{http_code}\n" -H "X-Forwarded-User: boss" http://127.0.0.1:3000/api/datasources
curl -sS -o /tmp/gf-search.json -w "search_http=%{http_code}\n" -H "X-Forwarded-User: boss" "http://127.0.0.1:3000/api/search?type=dash-db"
python3 - <<'PY'
import json
ds = json.load(open("/tmp/gf-ds.json"))
print("datasources=", [d.get("name") for d in ds] if isinstance(ds, list) else ds)
search = json.load(open("/tmp/gf-search.json"))
print("dashboards=", [d.get("title") for d in search] if isinstance(search, list) else search)
PY

echo
echo "Open https://grafana.clawsum.com  (Authelia once) → Clawsum Health dashboard"
echo "Prometheus (SSH tunnel): ssh -L 9090:127.0.0.1:9090 root@VPS → http://127.0.0.1:9090"
