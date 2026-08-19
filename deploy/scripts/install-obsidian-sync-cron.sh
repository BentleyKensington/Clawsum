#!/usr/bin/env bash
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

CRON_LINE='*/15 * * * * /bin/bash /docker/clawsum/scripts/sync-obsidian-reports.sh >> /docker/clawsum/data/reports/obsidian-sync.log 2>&1'
install_cron_line 'sync-obsidian-reports.sh' "$CRON_LINE"
echo "Obsidian sync cron (every 15m, America/Chicago):"
crontab -l | grep -E 'CRON_TZ|sync-obsidian' || true
