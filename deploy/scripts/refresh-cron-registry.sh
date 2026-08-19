#!/usr/bin/env bash
# Dump host crontab so the cockpit Cron page shows live Clawsum jobs.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
OUT="$ROOT/data/reports"
mkdir -p "$OUT"
crontab -l > "$OUT/cron-live.txt" 2>/dev/null || true
python3 - <<'PY'
import json
from pathlib import Path
root = Path("/docker/clawsum")
jobs = [
    {"id": "daily-brief", "name": "Morning Boss brief", "schedule": "07:30 Chicago", "marker": "run-daily-global-report.sh", "href": "/home?tab=brief"},
    {"id": "agent-review", "name": "Agent daily reviews", "schedule": "with morning brief", "marker": "daily-agent-review.py", "href": "/home?tab=brief"},
    {"id": "gmail-sync", "name": "Gmail sync", "schedule": "every 15m", "marker": "gmail-sync.py", "href": "/inbox"},
    {"id": "gmail-review", "name": "Gmail inbox review", "schedule": "gmail-inbox-review", "marker": "gmail-inbox-review", "href": "/inbox"},
    {"id": "gmail-triage", "name": "Gmail triage", "schedule": ":17/:47", "marker": "gmail-triage.py", "href": "/inbox"},
    {"id": "memory-dream", "name": "Night memory dream", "schedule": "Chicago night window", "marker": "run-memory-dream.sh", "href": "/home?tab=archive"},
    {"id": "archive-obsidian", "name": "Archive → Obsidian", "schedule": "hourly :40", "marker": "poll-archive-to-obsidian.py", "href": "/home?tab=graph"},
    {"id": "obsidian-sync", "name": "Obsidian report sync", "schedule": "every 15m", "marker": "sync-obsidian-reports.sh", "href": "/home?tab=graph"},
    {"id": "reminders", "name": "Boss reminders", "schedule": "daily", "marker": "reminders-notify.py", "href": "/inbox"},
    {"id": "ghl-weekly", "name": "GHL weekly REI", "schedule": "Mon 08:00", "marker": "ghl-weekly-report.py", "href": "/agents"},
    {"id": "outage-watch", "name": "Chat outage watch", "schedule": "frequent", "marker": "chat-outage-watch.py", "href": "/home?tab=channels"},
]
Path("/docker/clawsum/data/reports/cron-registry.json").write_text(
    json.dumps({"jobs": jobs}, indent=2) + "\n", encoding="utf-8"
)
print("cron-registry.json", len(jobs))
PY
echo "wrote $OUT/cron-live.txt"
wc -l "$OUT/cron-live.txt" || true
