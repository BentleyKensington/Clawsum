#!/usr/bin/env bash
# Install memory dreaming crons (true America/Chicago via in-script gates).
# Hourly: :20 every hour — dedupe / contradict / expire
# Nightly: 02:15 Chicago — LLM compress + Obsidian Admin/Memory dream note
# Weekly: Sunday 03:30 Chicago — deeper dream + Self-Model touch
#
# Ubuntu cron ignores CRON_TZ here, so nightly/weekly wrappers run hourly and
# gate inside run-memory-dream.sh (same pattern as the morning Boss brief).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
# shellcheck source=lib/ensure-cron-tz.sh
source "${SCRIPT_DIR}/lib/ensure-cron-tz.sh"

RUNNER="${ROOT}/scripts/run-memory-dream.sh"
chmod +x "${ROOT}/scripts/memory-dream.py" "${RUNNER}" 2>/dev/null || true

# Drop legacy UTC-scheduled lines before installing gated ones
existing="$(crontab -l 2>/dev/null || true)"
{
  echo "CRON_TZ=America/Chicago"
  echo "${existing}" \
    | grep -v '^CRON_TZ=' \
    | grep -v 'run-memory-dream.sh' \
    || true
  echo "20 * * * * /bin/bash /docker/clawsum/scripts/run-memory-dream.sh hourly >> /docker/clawsum/data/reports/memory-dream-hourly.log 2>&1"
  echo "15 * * * * /bin/bash /docker/clawsum/scripts/run-memory-dream.sh nightly >> /docker/clawsum/data/reports/memory-dream-nightly.log 2>&1"
  echo "30 * * * * /bin/bash /docker/clawsum/scripts/run-memory-dream.sh weekly >> /docker/clawsum/data/reports/memory-dream-weekly.log 2>&1"
} | crontab -

mkdir -p /docker/clawsum/data/reports /docker/clawsum/obsidian/Admin/Memory
chown -R 1000:1000 /docker/clawsum/obsidian/Admin/Memory 2>/dev/null || true

echo "Installed memory dream crons (Chicago-gated nightly 02:15 / weekly Sun 03:30):"
crontab -l | grep -E 'CRON_TZ|memory-dream|run-memory-dream' || true
