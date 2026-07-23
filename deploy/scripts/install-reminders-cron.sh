#!/usr/bin/env bash
# Daily reminders at 7:05 America/Chicago (after main global report at 7:00)
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

LINE='5 7 * * * /usr/bin/python3 /docker/clawsum/scripts/reminders-notify.py >> /docker/clawsum/data/reports/reminders.log 2>&1'
install_cron_line 'reminders-notify.py' "$LINE"
echo "Installed (7:05 America/Chicago):"
crontab -l | grep -E 'CRON_TZ|reminders-notify' || true
