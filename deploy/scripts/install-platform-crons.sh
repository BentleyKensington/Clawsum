#!/bin/bash
# Install platform crons (backup, notifier, Obsidian sync, docs backfill).
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"
MARK="# clawsum-platform-cron"

# 03:00 America/Chicago — Ubuntu cron ignores CRON_TZ, so hourly :00 + gate
backup_line="0 * * * * /bin/bash ${ROOT}/scripts/run-at-chicago.sh 3 0 4 -- /bin/bash ${ROOT}/scripts/backup-platform.sh >> ${ROOT}/data/backups/backup.log 2>&1 ${MARK}-backup"

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

if [[ -f "${SCRIPT_DIR}/sync-obsidian-reports.sh" ]] || [[ -f scripts/sync-obsidian-reports.sh ]]; then
  obsidian_line="*/15 * * * * cd ${ROOT} && bash scripts/sync-obsidian-reports.sh >> data/reports/obsidian-sync.log 2>&1 ${MARK}-obsidian"
  if crontab -l 2>/dev/null | grep -q 'sync-obsidian-reports.sh'; then
    echo "OK obsidian sync cron already installed"
    ensure_cron_tz
  else
    install_cron_line "${MARK}-obsidian" "$obsidian_line"
    echo "Installed Obsidian sync cron (every 15 min)"
  fi
fi

if [[ -f "${SCRIPT_DIR}/clawsum_docs_etl.py" ]] || [[ -f scripts/clawsum_docs_etl.py ]]; then
  docs_line="*/15 * * * * cd ${ROOT} && python3 scripts/clawsum_docs_etl.py --backfill-media >> data/reports/docs-etl-backfill.log 2>&1 ${MARK}-docs"
  if crontab -l 2>/dev/null | grep -q "${MARK}-docs"; then
    echo "OK docs ETL backfill cron already installed"
    ensure_cron_tz
  else
    install_cron_line "${MARK}-docs" "$docs_line"
    echo "Installed docs ETL backfill cron (every 15 min)"
  fi
fi

if [[ -f "${SCRIPT_DIR}/install-memory-dream-cron.sh" ]]; then
  bash "${SCRIPT_DIR}/install-memory-dream-cron.sh" || true
fi

# 7:30 America/Chicago daily global report
if [[ -f "${SCRIPT_DIR}/install-daily-report-cron.sh" ]]; then
  bash "${SCRIPT_DIR}/install-daily-report-cron.sh" || true
fi

# Monday weekly GHL REI reports (MCO + Avenou) — optional if accounts configured
if [[ -f "${SCRIPT_DIR}/install-ghl-weekly-report-cron.sh" ]]; then
  bash "${SCRIPT_DIR}/install-ghl-weekly-report-cron.sh" || true
fi

if [[ -f "${SCRIPT_DIR}/install-hermes-keepalive-cron.sh" ]]; then
  bash "${SCRIPT_DIR}/install-hermes-keepalive-cron.sh" || true
fi

if [[ -f "${SCRIPT_DIR}/install-content-factory-cron.sh" ]]; then
  bash "${SCRIPT_DIR}/install-content-factory-cron.sh" || true
fi

if [[ -f "${SCRIPT_DIR}/install-nightly-last-session-cron.sh" ]]; then
  bash "${SCRIPT_DIR}/install-nightly-last-session-cron.sh" || true
fi
