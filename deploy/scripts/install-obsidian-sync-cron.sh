#!/usr/bin/env bash
set -eu
CRON_LINE='2 7 * * * TZ=America/Chicago /bin/bash /docker/clawsum/scripts/sync-obsidian-reports.sh >> /docker/clawsum/data/reports/obsidian-sync.log 2>&1'
( crontab -l 2>/dev/null | grep -v 'sync-obsidian-reports.sh' || true
  echo "$CRON_LINE"
) | crontab -
echo "Obsidian report sync cron (7:02 daily):"
crontab -l | grep sync-obsidian
