#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
mkdir -p "$R/scripts" "$R/docs" "$R/prometheus/alerts"
cp -f /tmp/ensure-hermes-runtime.sh "$R/scripts/ensure-hermes-runtime.sh"
cp -f /tmp/hermes-dashboard.sh "$R/scripts/hermes-dashboard.sh"
cp -f /tmp/hermes-config-safe.py "$R/scripts/hermes-config-safe.py"
cp -f /tmp/install-hermes-keepalive-cron.sh "$R/scripts/install-hermes-keepalive-cron.sh"
cp -f /tmp/_rewrite-hermes-config.sh "$R/scripts/_rewrite-hermes-config.sh"
cp -f /tmp/install-platform-crons.sh "$R/scripts/install-platform-crons.sh"
cp -f /tmp/_fix-boss-chat-token.sh "$R/scripts/_fix-boss-chat-token.sh"
cp -f /tmp/clawsum-alerts.yml "$R/prometheus/alerts/clawsum.yml"
cp -f /tmp/HERMES-POLICY.md "$R/docs/HERMES-POLICY.md"
chmod +x "$R/scripts/ensure-hermes-runtime.sh" \
  "$R/scripts/hermes-dashboard.sh" \
  "$R/scripts/hermes-config-safe.py" \
  "$R/scripts/install-hermes-keepalive-cron.sh" \
  "$R/scripts/_rewrite-hermes-config.sh"
sed -i 's/\r$//' "$R/scripts/ensure-hermes-runtime.sh" \
  "$R/scripts/hermes-dashboard.sh" \
  "$R/scripts/hermes-config-safe.py" \
  "$R/scripts/install-hermes-keepalive-cron.sh" \
  "$R/scripts/_rewrite-hermes-config.sh"
bash "$R/scripts/install-hermes-keepalive-cron.sh"
echo "=== cron ==="
cat /etc/cron.d/clawsum-hermes-dashboard
echo "=== systemd ==="
systemctl is-enabled clawsum-hermes-runtime.service || true
echo "=== status ==="
bash "$R/scripts/hermes-dashboard.sh" status
curl -sS http://127.0.0.1:9119/api/status
echo
test -f "$R/paperclip-data/.hermes/config.yaml.ok" && echo config_ok_snapshot || echo no_ok_snapshot
test -f "$R/data/prometheus-textfile/hermes_gateway.prom" && cat "$R/data/prometheus-textfile/hermes_gateway.prom" || true
