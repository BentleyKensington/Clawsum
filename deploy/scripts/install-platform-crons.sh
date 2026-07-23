#!/bin/bash
# Install platform crons (backup, optional Grafana→Telegram notifier).
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"
MARK="# clawsum-platform-cron"

# 03:00 America/Chicago (CRON_TZ) — night backup, not UTC
backup_line="0 3 * * * cd ${ROOT} && bash scripts/backup-platform.sh >> data/backups/backup.log 2>&1 ${MARK}-backup"

if crontab -l 2>/dev/null | grep -q "${MARK}-backup"; then
  echo "OK backup cron already installed"
  ensure_cron_tz
else
  install_cron_line "${MARK}-backup" "$backup_line"
  echo "Installed backup cron (03:00 America/Chicago)"
fi

if [[ -x "${SCRIPT_DIR}/grafana-telegram-notifier.sh" ]] || [[ -x scripts/grafana-telegram-notifier.sh ]]; then
  alert_line="*/5 * * * * cd ${ROOT} && bash scripts/grafana-telegram-notifier.sh >> data/backups/grafana-alerts.log 2>&1 ${MARK}-grafana"
  if crontab -l 2>/dev/null | grep -q "${MARK}-grafana"; then
    echo "OK grafana notifier cron already installed"
    ensure_cron_tz
  else
    install_cron_line "${MARK}-grafana" "$alert_line"
    echo "Installed Grafana notifier cron (every 5 min)"
  fi
fi
