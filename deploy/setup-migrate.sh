#!/bin/bash
# Migrate Hostinger OpenClaw data to Clawsum self-hosted stack
set -euo pipefail

HOST=/docker/openclaw-qpr7
CLAWSUM=/docker/clawsum
SRC="$HOST/data/.openclaw"
DST="$CLAWSUM/data/.openclaw"

echo "==> Migrating .openclaw from Hostinger to Clawsum..."
mkdir -p "$DST"

# Full copy preserving structure (exclude lock files)
rsync -a --delete \
  --exclude='*.lock' \
  "$SRC/" "$DST/"

# Ensure all agent workspaces exist
for ws in admin coding data realestate ghl comms research planning; do
  mkdir -p "$DST/workspace-${ws}"
  mkdir -p "$CLAWSUM/obsidian/${ws^}"
done

# Promote main workspace to admin if not present
if [ -d "$DST/workspace" ] && [ ! -f "$DST/workspace-admin/SOUL.md" ]; then
  echo "==> Seeding workspace-admin from workspace (main)..."
  rsync -a "$DST/workspace/" "$DST/workspace-admin/" || true
fi

# Fix ownership for node user (uid 1000)
chown -R 1000:1000 "$CLAWSUM/data" "$CLAWSUM/obsidian" 2>/dev/null || true
chmod 600 "$DST/openclaw.json" 2>/dev/null || true
chown 1000:1000 "$DST/openclaw.json" 2>/dev/null || true

echo "==> Migration copy complete."
echo "    Next: sanitize openclaw.json (agents list, whatsapp -> comms only)"
echo "    Then: docker compose up -d postgres arcadedb openclaw-gateway"
