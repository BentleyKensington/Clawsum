#!/bin/bash
# Forward firing Prometheus alerts (via Grafana) to Discord + Telegram (dual-write).
# Requires: GRAFANA_ADMIN_PASSWORD; Discord and/or Telegram via clawsum_notify.
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"

set -a
# shellcheck disable=SC1091
source .env 2>/dev/null || true
set +a

GPASS="${GRAFANA_ADMIN_PASSWORD:-}"
[[ -n "$GPASS" ]] || exit 0

ALERTS=$(curl -sf -u "admin:${GPASS}" "http://127.0.0.1:3000/api/prometheus/grafana/api/v1/alerts" 2>/dev/null || true)
[[ -n "$ALERTS" ]] || exit 0

python3 - <<'PY' "$ALERTS"
import json, sys
from pathlib import Path

sys.path.insert(0, "/docker/clawsum/scripts")
from clawsum_notify import notify_boss, any_ok, load_env

raw = sys.argv[1]
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(0)

firing = []
for item in data.get("data", {}).get("alerts", []):
    if item.get("state") == "firing":
        labels = item.get("labels", {})
        firing.append(f"{labels.get('alertname','alert')}: {labels.get('severity','')}")

if not firing:
    sys.exit(0)

text = "Clawsum alerts firing:\n" + "\n".join(f"- {x}" for x in firing[:10])
results = notify_boss(text, severity="critical", env=load_env())
if not any_ok(results):
    sys.exit(1)
PY
