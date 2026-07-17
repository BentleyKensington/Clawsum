#!/bin/bash
# Forward firing Prometheus alerts (via Grafana) to Admin Telegram when configured.
# Requires: GRAFANA_ADMIN_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_CHAT_ID in .env
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"

set -a
# shellcheck disable=SC1091
source .env 2>/dev/null || true
set +a

TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT="${TELEGRAM_ADMIN_CHAT_ID:-}"
GPASS="${GRAFANA_ADMIN_PASSWORD:-}"

[[ -n "$TOKEN" && -n "$CHAT" ]] || exit 0

ALERTS=$(curl -sf -u "admin:${GPASS}" "http://127.0.0.1:3000/api/prometheus/grafana/api/v1/alerts" 2>/dev/null || true)
[[ -n "$ALERTS" ]] || exit 0

python3 - <<'PY' "$ALERTS" "$TOKEN" "$CHAT"
import json, sys, urllib.request

raw, token, chat = sys.argv[1:4]
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
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data=json.dumps({"chat_id": chat, "text": text}).encode(),
    headers={"Content-Type": "application/json"},
)
urllib.request.urlopen(req, timeout=15)
PY
