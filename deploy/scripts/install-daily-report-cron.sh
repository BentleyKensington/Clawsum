#!/usr/bin/env bash
# Install 7:00 America/Chicago daily global report cron on the VPS.
# Uses CRON_TZ so the schedule is Chicago time (not UTC — UTC 07:00 ≈ 02:00 CDT).
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

SCRIPT="/docker/clawsum/scripts/daily-global-report.py"
CRON_LINE='0 7 * * * /usr/bin/python3 /docker/clawsum/scripts/daily-global-report.py >> /docker/clawsum/data/reports/cron.log 2>&1'

mkdir -p /docker/clawsum/data/reports
chmod +x "$SCRIPT" 2>/dev/null || true

install_cron_line 'daily-global-report.py' "$CRON_LINE"

echo "Installed cron (CRON_TZ=America/Chicago → 07:00 CST/CDT):"
crontab -l | grep -E 'CRON_TZ|daily-global-report' || true
echo "Test run (dry-run):"
python3 "$SCRIPT" --dry-run | head -25
