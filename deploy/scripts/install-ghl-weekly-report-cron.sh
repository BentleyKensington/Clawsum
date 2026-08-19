#!/bin/bash
# Nightly generate + 07:30 America/Chicago send for GHL REI reports.
# Ubuntu cron ignores CRON_TZ — hourly fire + run-at-chicago.sh gate.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

mkdir -p /docker/clawsum/data/reports/ghl-weekly
chmod +x /docker/clawsum/scripts/run-at-chicago.sh 2>/dev/null || true

PY='/usr/bin/python3 /docker/clawsum/scripts/ghl-weekly-report.py --slugs mco-rei,ave-rei,dispo-dudes'
LOG='/docker/clawsum/data/reports/ghl-weekly/cron.log'
GATE='/bin/bash /docker/clawsum/scripts/run-at-chicago.sh'

existing="$(crontab -l 2>/dev/null || true)"
{
  echo "CRON_TZ=America/Chicago"
  echo "${existing}" | grep -v '^CRON_TZ=' | grep -v 'ghl-weekly-report.py' | grep -v 'ghl-daily-report' || true
} | crontab -

# :00 every hour — only executes at 22:00 Chicago
GEN_LINE="0 * * * * ${GATE} 22 0 4 -- ${PY} --audit --use-llm --no-notify >> ${LOG} 2>&1 # ghl-daily-report-generate"
# :30 every hour — only executes at 07:30 Chicago
SEND_LINE="30 * * * * ${GATE} 7 30 4 -- ${PY} --no-audit --notify >> ${LOG} 2>&1 # ghl-daily-report-send"

install_cron_line 'ghl-daily-report-generate' "$GEN_LINE"
install_cron_line 'ghl-daily-report-send' "$SEND_LINE"

echo "Installed GHL REI report crons (Chicago-gated; UTC cron ignored):"
echo "  hourly :00 — generate only at 22:00 America/Chicago"
echo "  hourly :30 — send only at 07:30 America/Chicago"
crontab -l | grep -E 'CRON_TZ|ghl-daily-report|ghl-weekly-report|run-at-chicago' || true
