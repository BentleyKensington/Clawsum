#!/usr/bin/env bash
# Install Hermes dashboard+gateway keepalive (cron + systemd After=docker).
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
CRON_FILE=/etc/cron.d/clawsum-hermes-dashboard
UNIT=/etc/systemd/system/clawsum-hermes-runtime.service

chmod +x "$ROOT/scripts/ensure-hermes-runtime.sh" \
  "$ROOT/scripts/hermes-dashboard.sh" \
  "$ROOT/scripts/hermes-config-safe.py" 2>/dev/null || true

cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
*/2 * * * * root $ROOT/scripts/ensure-hermes-runtime.sh >>/var/log/clawsum-hermes-runtime.log 2>&1
@reboot root sleep 60 && $ROOT/scripts/ensure-hermes-runtime.sh >>/var/log/clawsum-hermes-runtime.log 2>&1
EOF
chmod 644 "$CRON_FILE"

cat > "$UNIT" <<EOF
[Unit]
Description=Clawsum Hermes dashboard + gateway
After=docker.service
Wants=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$ROOT/scripts/ensure-hermes-runtime.sh
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable clawsum-hermes-runtime.service >/dev/null
systemctl start clawsum-hermes-runtime.service || true

echo "installed $CRON_FILE"
echo "enabled clawsum-hermes-runtime.service"
bash "$ROOT/scripts/ensure-hermes-runtime.sh"
echo KEEPALIVE_OK
