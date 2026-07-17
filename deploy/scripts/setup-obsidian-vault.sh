#!/usr/bin/env bash
# Full Obsidian vault setup on VPS (idempotent).
set -euo pipefail
ROOT=/docker/clawsum/scripts
for s in normalize-obsidian-vault.sh seed-obsidian-vault.sh sync-obsidian-reports.sh install-obsidian-sync-cron.sh; do
  sed -i 's/\r$//' "$ROOT/$s" 2>/dev/null || true
  bash "$ROOT/$s"
done
echo ""
echo "Obsidian vault ready. Open /docker/clawsum/obsidian on your PC (git/Syncthing/SSHFS)."
