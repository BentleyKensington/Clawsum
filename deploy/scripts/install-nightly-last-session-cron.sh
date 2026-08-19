#!/usr/bin/env bash
# Nightly LAST_SESSION.md rewrite at 21:00 America/Chicago.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

ROOT=/docker/clawsum
chmod +x "$ROOT/scripts/nightly-last-session.py" "$ROOT/scripts/run-at-chicago.sh" 2>/dev/null || true
LINE="0 * * * * /bin/bash $ROOT/scripts/run-at-chicago.sh 21 0 4 -- /usr/bin/python3 $ROOT/scripts/nightly-last-session.py >> $ROOT/data/reports/last-session-nightly.log 2>&1"
install_cron_line 'nightly-last-session.py' "$LINE"
echo "Installed nightly LAST_SESSION rewrite (21:00 America/Chicago):"
crontab -l | grep -E 'CRON_TZ|nightly-last-session' || true
