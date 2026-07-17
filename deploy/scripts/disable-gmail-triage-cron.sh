#!/bin/bash
# Stop auto-creating Paperclip tasks from Gmail while Boss queue is paused.
set -euo pipefail
(crontab -l 2>/dev/null | grep -v gmail-triage.py || true) | crontab -
echo "Removed gmail-triage cron (gmail-sync still runs; no new tasks until triage re-enabled)."
