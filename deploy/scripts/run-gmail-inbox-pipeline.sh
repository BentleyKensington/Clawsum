#!/usr/bin/env bash
# Sync clawsums@gmail.com → analyze every message for Hermes / cockpit Inbox.
# Called by cron (install-gmail-inbox-review-cron.sh) and manually.
set -euo pipefail
ROOT=/docker/clawsum
SCRIPTS="${ROOT}/scripts"
LOG_DIR="${ROOT}/data/reports"
REPORT_DIR="${ROOT}/data/inbox-reports"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

cd "$ROOT"
echo "[$(date -Is)] gmail inbox pipeline start"

python3 "${SCRIPTS}/gmail-sync.py" || {
  echo "[$(date -Is)] gmail-sync failed" >&2
  exit 1
}

# --all so new + previously unanalyzed messages get reports
# --inbox-only focuses on the mailbox Hermes monitors
python3 "${SCRIPTS}/gmail-inbox-review.py" \
  --inbox-only \
  --all \
  --markdown \
  --create-reminders \
  --report-dir "${REPORT_DIR}" || {
  echo "[$(date -Is)] gmail-inbox-review failed" >&2
  exit 1
}

echo "[$(date -Is)] gmail inbox pipeline ok"
