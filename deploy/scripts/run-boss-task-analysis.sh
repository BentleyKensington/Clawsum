#!/bin/bash
# Analyze master list + Gmail tasks → assign agents + Boss clarification questions.
set -euo pipefail
cd /docker/clawsum

echo "=== Gmail pending triage ==="
python3 scripts/gmail-triage.py --limit 50 || true

echo "=== CLA-1 delegation (idempotent) ==="
python3 scripts/paperclip-delegate-task-list.py --issue CLA-1 2>/dev/null || \
  python3 scripts/paperclip-delegate-task-list.py --issue-id 1d387205-2ac2-40b2-8418-d6ff26e835c7 2>/dev/null || true

echo "=== Analyze, assign, Boss questions ==="
python3 scripts/paperclip-analyze-assign-boss.py --status blocked,todo,backlog

echo "=== Status ==="
python3 scripts/paperclip-task-status.py | head -40
