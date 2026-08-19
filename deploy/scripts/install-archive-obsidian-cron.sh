#!/usr/bin/env bash
# Poll ChatGPT archive → Obsidian memory every hour at :40 UTC
# (wrapper is cheap; script is incremental).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh" 2>/dev/null || true

LINE='40 * * * * /usr/bin/python3 /docker/clawsum/scripts/poll-archive-to-obsidian.py >> /docker/clawsum/data/reports/archive-obsidian-poll.log 2>&1'
existing="$(crontab -l 2>/dev/null || true)"
{
  echo "CRON_TZ=America/Chicago"
  echo "${existing}" | grep -v '^CRON_TZ=' | grep -v 'poll-archive-to-obsidian.py' || true
  echo "$LINE"
} | crontab -

echo "Installed archive → Obsidian poll (hourly :40):"
crontab -l | grep -E 'CRON_TZ|poll-archive' || true
