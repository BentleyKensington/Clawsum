#!/usr/bin/env bash
# Install daily Boss brief at 7:30am America/Chicago.
# NOTE: Ubuntu cron on the VPS ignores CRON_TZ — schedule hourly at :30 and
# let run-daily-global-report.sh gate on Chicago local time.
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

WRAPPER="/docker/clawsum/scripts/run-daily-global-report.sh"
CRON_LINE='30 * * * * /bin/bash /docker/clawsum/scripts/run-daily-global-report.sh'

mkdir -p /docker/clawsum/data/reports
chmod +x "$WRAPPER" /docker/clawsum/scripts/daily-global-report.py /docker/clawsum/scripts/daily-agent-review.py 2>/dev/null || true

# Remove old direct python cron + install wrapper
install_cron_line 'daily-global-report.py' "$CRON_LINE"
install_cron_line 'run-daily-global-report.sh' "$CRON_LINE"

echo "Installed Boss brief cron:"
echo "  UTC schedule: every hour at :30"
echo "  Gate: only runs at 07:30 America/Chicago (ignores other hours)"
crontab -l | grep -E 'CRON_TZ|daily-global|run-daily-global' || true
echo "Dry-run brief:"
python3 /docker/clawsum/scripts/daily-global-report.py --dry-run | head -40
