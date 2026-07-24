#!/usr/bin/env bash
# Sync clawsums@gmail.com → analyze every message for Hermes / cockpit Inbox.
# Called by cron (install-gmail-inbox-review-cron.sh) and manually.
# On OAuth / sync failure: Telegram-alerts Boss (gmail_oauth_health.py).
set -euo pipefail
ROOT=/docker/clawsum
SCRIPTS="${ROOT}/scripts"
LOG_DIR="${ROOT}/data/reports"
REPORT_DIR="${ROOT}/data/inbox-reports"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

cd "$ROOT"
echo "[$(date -Is)] gmail inbox pipeline start"

# Preflight OAuth — alerts Boss if broken (cooldown-aware)
if ! python3 "${SCRIPTS}/gmail_oauth_health.py"; then
  echo "[$(date -Is)] gmail oauth health failed — Boss should be alerted" >&2
  exit 2
fi

if ! python3 "${SCRIPTS}/gmail-sync.py"; then
  echo "[$(date -Is)] gmail-sync failed" >&2
  python3 "${SCRIPTS}/gmail_oauth_health.py" --from-failure "gmail-sync exited non-zero" || true
  exit 1
fi

# --all so new + previously unanalyzed messages get reports
# --inbox-only focuses on the mailbox Hermes monitors
if ! python3 "${SCRIPTS}/gmail-inbox-review.py" \
  --inbox-only \
  --all \
  --markdown \
  --create-reminders \
  --report-dir "${REPORT_DIR}"; then
  echo "[$(date -Is)] gmail-inbox-review failed" >&2
  exit 1
fi

echo "[$(date -Is)] gmail inbox pipeline ok"
