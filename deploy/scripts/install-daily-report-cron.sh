#!/usr/bin/env bash
# Install 7:00 America/Chicago daily global report cron on the VPS.
set -eu
SCRIPT="/docker/clawsum/scripts/daily-global-report.py"
CRON_LINE='0 7 * * * TZ=America/Chicago /usr/bin/python3 /docker/clawsum/scripts/daily-global-report.py >> /docker/clawsum/data/reports/cron.log 2>&1'

mkdir -p /docker/clawsum/data/reports
chmod +x "$SCRIPT" 2>/dev/null || true

# Idempotent: replace existing line if present
( crontab -l 2>/dev/null | grep -v 'daily-global-report.py' || true
  echo "$CRON_LINE"
) | crontab -

echo "Installed cron:"
crontab -l | grep daily-global-report || true
echo "Test run (dry-run):"
python3 "$SCRIPT" --dry-run | head -25
