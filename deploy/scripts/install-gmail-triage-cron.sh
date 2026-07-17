#!/bin/bash
# Cron: triage pending Gmail every 30 min (after gmail-sync at :15)
set -euo pipefail
CRON_LINE='17,47 * * * * cd /docker/clawsum && /usr/bin/python3 /docker/clawsum/scripts/gmail-triage.py --limit 15 >> /docker/clawsum/data/logs/gmail-triage.log 2>&1'
mkdir -p /docker/clawsum/data/logs
(crontab -l 2>/dev/null | grep -v gmail-triage.py; echo "$CRON_LINE") | crontab -
echo "Installed gmail-triage cron ( :17 and :47 each hour )"
