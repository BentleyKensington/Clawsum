#!/usr/bin/env bash
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

CRON_LINE='2 7 * * * /bin/bash /docker/clawsum/scripts/sync-obsidian-reports.sh >> /docker/clawsum/data/reports/obsidian-sync.log 2>&1'
install_cron_line 'sync-obsidian-reports.sh' "$CRON_LINE"
echo "Obsidian report sync cron (7:02 America/Chicago):"
crontab -l | grep -E 'CRON_TZ|sync-obsidian' || true
