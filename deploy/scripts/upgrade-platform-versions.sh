#!/bin/bash
# Upgrade OpenClaw + Paperclip to pinned stable versions (see deploy/docs/VERSION-PINNING.md).
# Run on VPS during a maintenance window; heartbeats should stay OFF until smoke tests pass.
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
OPENCLAW_IMAGE="${OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:2026.6.10}"
PAPERCLIP_IMAGE="${PAPERCLIP_IMAGE:-ghcr.io/paperclipai/paperclip:latest}"
BACKUP="${BACKUP:-1}"

cd "$ROOT"

echo "=== Clawsum platform version upgrade ==="
echo "OpenClaw:  $OPENCLAW_IMAGE"
echo "Paperclip: $PAPERCLIP_IMAGE"
echo ""

if [[ "$BACKUP" == "1" ]]; then
  STAMP="$(date +%Y%m%d-%H%M%S)"
  BK="$ROOT/data/backups/pre-upgrade-$STAMP"
  mkdir -p "$BK"
  echo "Backing up .openclaw + paperclip-data to $BK ..."
  tar -czf "$BK/openclaw.tgz" -C "$ROOT/data" .openclaw 2>/dev/null || true
  tar -czf "$BK/paperclip-data.tgz" -C "$ROOT" paperclip-data 2>/dev/null || true
  echo "Backup done."
fi

# Persist pins in .env (idempotent)
touch .env
grep -q '^OPENCLAW_IMAGE=' .env && sed -i "s|^OPENCLAW_IMAGE=.*|OPENCLAW_IMAGE=$OPENCLAW_IMAGE|" .env \
  || echo "OPENCLAW_IMAGE=$OPENCLAW_IMAGE" >> .env
grep -q '^PAPERCLIP_IMAGE=' .env && sed -i "s|^PAPERCLIP_IMAGE=.*|PAPERCLIP_IMAGE=$PAPERCLIP_IMAGE|" .env \
  || echo "PAPERCLIP_IMAGE=$PAPERCLIP_IMAGE" >> .env

export OPENCLAW_IMAGE PAPERCLIP_IMAGE

echo ""
echo "=== Pull images ==="
docker compose pull openclaw-gateway openclaw-cli 2>/dev/null || docker compose pull openclaw-gateway
docker compose --profile orchestration pull paperclip || {
  echo "WARN: pinned Paperclip tag missing on GHCR — using latest"
  export PAPERCLIP_IMAGE=ghcr.io/paperclipai/paperclip:latest
  docker compose --profile orchestration pull paperclip
}

echo ""
echo "=== Recreate OpenClaw gateway ==="
docker compose up -d openclaw-gateway
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:48166/healthz >/dev/null; then
    echo "Gateway healthy."
    break
  fi
  sleep 2
done
docker exec clawsum-openclaw-gateway-1 node dist/index.js --version || true

echo ""
echo "=== Recreate Paperclip ==="
docker compose --profile orchestration up -d paperclip
sleep 5

echo ""
echo "=== Paperclip ↔ OpenClaw protocol patch (if still v3) ==="
if bash "$ROOT/scripts/fix-paperclip-openclaw-protocol.sh"; then
  echo "Protocol patch applied."
else
  echo "Protocol patch skipped or failed — check if new Paperclip image already ships v4."
fi

echo ""
echo "=== Re-wire Paperclip execution adapters ==="
python3 "$ROOT/scripts/paperclip-fix-execution.py" --skip-protocol || true
python3 "$ROOT/scripts/fix-paperclip-pairing-scopes.py" 2>/dev/null || true

echo ""
echo "=== Smoke tests ==="
bash "$ROOT/scripts/telegram-smoke-test.sh"
python3 "$ROOT/scripts/verify-ghl-isolation.py" 2>/dev/null || echo "(GHL isolation verify skipped)"
python3 "$ROOT/scripts/bind-ghl-telegram.py" --status 2>/dev/null || true

echo ""
echo "=== Upgrade complete ==="
echo "Versions:"
docker exec clawsum-openclaw-gateway-1 node dist/index.js --version 2>/dev/null || true
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'openclaw|paperclip' | head -5
echo ""
echo "Next: manual @mention in Telegram groups (incl. CS GHL). Keep heartbeats OFF until Boss approves resume."
