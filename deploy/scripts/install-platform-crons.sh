#!/bin/bash
# Install platform crons (backup, optional Grafana→Telegram notifier).
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
MARK="# clawsum-platform-cron"

backup_line="0 3 * * * cd ${ROOT} && bash scripts/backup-platform.sh >> data/backups/backup.log 2>&1 ${MARK}-backup"

if crontab -l 2>/dev/null | grep -q "${MARK}-backup"; then
  echo "OK backup cron already installed"
else
  (crontab -l 2>/dev/null; echo "$backup_line") | crontab -
  echo "Installed backup cron (03:00 daily)"
fi

if [[ -x scripts/grafana-telegram-notifier.sh ]]; then
  alert_line="*/5 * * * * cd ${ROOT} && bash scripts/grafana-telegram-notifier.sh >> data/backups/grafana-alerts.log 2>&1 ${MARK}-grafana"
  if crontab -l 2>/dev/null | grep -q "${MARK}-grafana"; then
    echo "OK grafana notifier cron already installed"
  else
    (crontab -l 2>/dev/null; echo "$alert_line") | crontab -
    echo "Installed Grafana notifier cron (every 5 min)"
  fi
fi
