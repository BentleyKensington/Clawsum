#!/usr/bin/env bash
# Daily Boss brief — only runs at 07:30 America/Chicago.
# Ubuntu cron on this host ignores CRON_TZ (schedules as UTC), so we gate in-script.
set -eo pipefail
export TZ=America/Chicago
ROOT=/docker/clawsum
LOG="$ROOT/data/reports/cron.log"
MARKER_DIR="$ROOT/data/reports"
mkdir -p "$MARKER_DIR"

H=$(date +%-H)
M=$(date +%-M)
STAMP=$(date +%Y-%m-%d)
MARKER="$MARKER_DIR/.brief-sent-$STAMP"

# Window: 07:30–07:34 Chicago (cron fires every hour at :30)
if [ "$H" -ne 7 ] || [ "$M" -lt 30 ] || [ "$M" -gt 34 ]; then
  exit 0
fi
if [ -f "$MARKER" ]; then
  echo "$(date -Is) skip: already sent $STAMP" >> "$LOG"
  exit 0
fi

echo "$(date -Is) starting daily brief (Chicago $(date '+%H:%M %Z'))" >> "$LOG"
/usr/bin/python3 "$ROOT/scripts/daily-agent-review.py" >> "$LOG" 2>&1 || true
if /usr/bin/python3 "$ROOT/scripts/daily-global-report.py" >> "$LOG" 2>&1; then
  touch "$MARKER"
  echo "$(date -Is) ok" >> "$LOG"
else
  echo "$(date -Is) FAILED rc=$?" >> "$LOG"
  exit 1
fi
