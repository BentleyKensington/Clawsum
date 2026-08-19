#!/usr/bin/env bash
# Verify Clawsum's monitoring pipeline end to end.
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://127.0.0.1:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:3000}"

echo "== containers =="
cd "${ROOT}"
docker compose --profile monitoring ps \
  prometheus grafana blackbox node-exporter cadvisor postgres-exporter

echo "== cockpit metrics =="
python3 "${ROOT}/scripts/clawsum-ops-metrics.py"
metrics="$(<"${ROOT}/data/prometheus-textfile/clawsum_ops.prom")"
for name in \
  clawsum_ops_metrics_generated_timestamp_seconds \
  clawsum_authority_agents \
  clawsum_authority_skills \
  clawsum_postgres_up \
  clawsum_paperclip_api_up; do
  if ! grep -q "^${name} " <<<"${metrics}"; then
    echo "MISSING ${name}" >&2
    exit 1
  fi
  grep "^${name} " <<<"${metrics}"
done

echo "== prometheus targets =="
curl -fsS "${PROMETHEUS_URL}/api/v1/targets" | python3 -c '
import json, sys
data = json.load(sys.stdin)["data"]["activeTargets"]
bad = []
for target in data:
    labels = target.get("labels") or {}
    job = labels.get("job", "?")
    instance = labels.get("instance", "?")
    health = target.get("health", "?")
    print(f"{health:7} {job:24} {instance}")
    if health != "up":
        bad.append((job, instance, target.get("lastError")))
if bad:
    print("Unhealthy targets:", bad, file=sys.stderr)
    raise SystemExit(1)
'

echo "== dashboard provisioning =="
curl -fsS "${GRAFANA_URL}/api/health"
test -r "${ROOT}/grafana/provisioning/dashboards/json/clawsum-operations.json"
echo
echo "MONITORING_OK"
