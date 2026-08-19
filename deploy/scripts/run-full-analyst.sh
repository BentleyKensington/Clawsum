#!/usr/bin/env bash
# Full inbox + Paperclip re-analysis (ChatGPT-style, assign owner, adopt/compare).
set -eo pipefail
ROOT=/docker/clawsum
LOGDIR="$ROOT/data/reports"
mkdir -p "$LOGDIR"
echo "START_INBOX $(date -Is)" | tee -a "$LOGDIR/full-analyst-run.log"
python3 "$ROOT/scripts/gmail-inbox-review.py" \
  --all --limit 200 --markdown --create-reminders \
  > "$LOGDIR/inbox-full-analyst.md" \
  2> "$LOGDIR/inbox-full-analyst.err" || echo "INBOX_FAIL $?" | tee -a "$LOGDIR/full-analyst-run.log"
echo "END_INBOX $(date -Is)" | tee -a "$LOGDIR/full-analyst-run.log"
echo "START_TASKS $(date -Is)" | tee -a "$LOGDIR/full-analyst-run.log"
python3 "$ROOT/scripts/paperclip-analyze-assign-boss.py" \
  --force --status blocked,todo,backlog,in_progress --no-summary \
  > "$LOGDIR/tasks-full-analyst.log" 2>&1 || echo "TASKS_FAIL $?" | tee -a "$LOGDIR/full-analyst-run.log"
echo "END_TASKS $(date -Is)" | tee -a "$LOGDIR/full-analyst-run.log"
