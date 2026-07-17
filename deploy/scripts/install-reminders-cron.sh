#!/usr/bin/env bash
# Daily reminders at 7:05 (after main global report at 7:00)
set -eu
LINE='5 7 * * * TZ=America/Chicago /usr/bin/python3 /docker/clawsum/scripts/reminders-notify.py >> /docker/clawsum/data/reports/reminders.log 2>&1'
( crontab -l 2>/dev/null | grep -v 'reminders-notify.py' || true
  echo "$LINE"
) | crontab -
echo "Installed:"
crontab -l | grep reminders-notify
