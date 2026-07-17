#!/usr/bin/env bash
set -eu
CRON_LINE='*/15 * * * * TZ=America/Chicago /usr/bin/python3 /docker/clawsum/scripts/gmail-sync.py >> /docker/clawsum/data/reports/gmail-sync.log 2>&1'
( crontab -l 2>/dev/null | grep -v 'gmail-sync.py' || true
  echo "$CRON_LINE"
) | crontab -
echo "Gmail sync cron (every 15 min):"
crontab -l | grep gmail-sync
