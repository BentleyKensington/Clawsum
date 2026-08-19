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

# New + stale robotic reviews only (ChatGPT-style). Cap keeps the 15m cron cheap.
# --inbox-only focuses on the mailbox Hermes monitors
if ! python3 "${SCRIPTS}/gmail-inbox-review.py" \
    --inbox-only \
    --markdown \
    --create-reminders \
    --limit 12 \
    --report-dir "${REPORT_DIR}"; then
  echo "[$(date -Is)] gmail-inbox-review failed" >&2
  exit 1
fi

# Keep Obsidian/Admin/Inbox fresh from the latest inbox review output.
if ! bash "${SCRIPTS}/sync-obsidian-reports.sh"; then
  echo "[$(date -Is)] obsidian sync failed" >&2
  exit 1
fi

# Opportunistic document backfill keeps Postgres + Arcade current as text media arrives.
python3 "${SCRIPTS}/clawsum_docs_etl.py" --backfill-media || true

echo "[$(date -Is)] gmail inbox pipeline ok"
