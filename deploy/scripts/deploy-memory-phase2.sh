#!/usr/bin/env bash
# Deploy Phase 2 dreaming: scripts, crons, smoke hourly + nightly.
set -eo pipefail
ROOT=/docker/clawsum
mkdir -p "$ROOT/data/reports" "$ROOT/obsidian/Admin/Memory"
chmod +x "$ROOT/scripts/run-memory-dream.sh" \
         "$ROOT/scripts/install-memory-dream-cron.sh" \
         "$ROOT/scripts/memory-dream.py"

echo "=== hourly smoke ==="
bash "$ROOT/scripts/run-memory-dream.sh" hourly

echo "=== nightly (may take several minutes) ==="
bash "$ROOT/scripts/run-memory-dream.sh" nightly --max-subjects 20

echo "=== install crons ==="
bash "$ROOT/scripts/install-memory-dream-cron.sh"

echo "=== verify ==="
docker exec clawsum-postgres-1 psql -U clawsum -d clawsum -c \
  "SELECT status, count(*) FROM ops.memory_facts GROUP BY 1 ORDER BY 1;
   SELECT stage, ok, left(stats::text, 180) AS stats, started_at
     FROM ops.memory_dream_runs ORDER BY started_at DESC LIMIT 5;"
ls -la "$ROOT/obsidian/Admin/Memory" 2>/dev/null | tail -10 || true
ls -la "$ROOT/obsidian/Admin/Latest-Dream.md" 2>/dev/null || true
echo "DONE phase2"
