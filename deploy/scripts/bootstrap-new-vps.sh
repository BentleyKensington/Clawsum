#!/bin/bash
# Greenfield Clawsum bootstrap — new VPS (not Hostinger migration).
# Prereqs: Docker, docker compose, repo at /docker/clawsum, .env filled from deploy/env.example
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"

# Repo may be flat on VPS (scripts/) or nested (deploy/scripts/)
SCRIPTS="$ROOT/scripts"
DOCS="$ROOT/docs"
ENV_EXAMPLE="$ROOT/env.example"
[[ -d "$ROOT/deploy/scripts" ]] && SCRIPTS="$ROOT/deploy/scripts"
[[ -d "$ROOT/deploy/docs" ]] && DOCS="$ROOT/deploy/docs"
[[ -f "$ROOT/deploy/env.example" ]] && ENV_EXAMPLE="$ROOT/deploy/env.example"

echo "=== Clawsum greenfield bootstrap ==="
echo "Root: $ROOT"

if [[ ! -f .env ]]; then
  echo "ERROR: .env missing. Copy env.example to .env and configure."
  echo "  cp $ENV_EXAMPLE .env"
  exit 1
fi

# Normalize line endings if synced from Windows
find "$SCRIPTS" -name '*.sh' -exec sed -i 's/\r$//' {} + 2>/dev/null || true

echo ""
echo "==> Data directories"
mkdir -p data/postgres data/arcadedb data/prometheus data/grafana data/reports data/backups data/minio
mkdir -p obsidian config templates/ghl paperclip-data
chown -R 1000:1000 data/.openclaw 2>/dev/null || mkdir -p data/.openclaw
chown -R 65534:65534 data/prometheus 2>/dev/null || true
chown -R 472:472 data/grafana 2>/dev/null || true

# Sync deploy artifacts if repo layout uses deploy/ subfolder
if [[ -d deploy/config ]]; then
  cp -f deploy/config/ghl-accounts.json config/ 2>/dev/null || true
fi
if [[ -d deploy/templates/ghl ]]; then
  mkdir -p templates/ghl
  cp -rf deploy/templates/ghl/* templates/ghl/ 2>/dev/null || true
elif [[ -d deploy/templates/ghl-account ]]; then
  mkdir -p templates/ghl-account
  cp -rf deploy/templates/ghl-account/* templates/ghl-account/ 2>/dev/null || true
fi

echo ""
echo "==> Core services (postgres, arcadedb, gateway)"
docker compose up -d postgres arcadedb
docker compose up -d openclaw-gateway

echo "Waiting for gateway health..."
for i in $(seq 1 45); do
  if curl -sf http://127.0.0.1:${OPENCLAW_GATEWAY_PORT:-48166}/healthz >/dev/null 2>&1; then
    echo "Gateway healthy."
    break
  fi
  sleep 2
done

echo ""
echo "==> Persona + Obsidian + DB docs"
bash scripts/seed-persona-os.sh 2>/dev/null || true
bash scripts/setup-obsidian-vault.sh 2>/dev/null || python3 scripts/setup-obsidian-vault.py 2>/dev/null || true
bash scripts/seed-workspace-db-docs.sh 2>/dev/null || true
bash scripts/create-db-users.sh 2>/dev/null || true

echo ""
echo "==> OpenClaw + Paperclip"
python3 scripts/configure-openclaw.py 2>/dev/null || true
docker compose --profile orchestration up -d paperclip
sleep 8
bash scripts/fix-paperclip-openclaw-protocol.sh 2>/dev/null || true
python3 scripts/wire-paperclip-clawsum.py 2>/dev/null || true
python3 scripts/paperclip-fix-execution.py --skip-protocol 2>/dev/null || true
python3 scripts/fix-paperclip-pairing-scopes.py 2>/dev/null || true

echo ""
echo "==> GHL domain pack (if credentials present)"
if grep -qE '^GHL_.*_PIT=.+' .env 2>/dev/null; then
  python3 scripts/provision-ghl-accounts.py --skip-paperclip 2>/dev/null || true
  python3 scripts/verify-ghl-isolation.py 2>/dev/null || true
else
  echo "SKIP GHL — no GHL_*_PIT in .env"
fi

echo ""
echo "==> Crons (install scripts — disable triage if Boss pause)"
bash scripts/install-gmail-sync-cron.sh 2>/dev/null || true
bash scripts/install-daily-report-cron.sh 2>/dev/null || true
bash scripts/install-reminders-cron.sh 2>/dev/null || true
bash scripts/install-obsidian-sync-cron.sh 2>/dev/null || true

echo ""
echo "==> Monitoring (optional profile)"
bash scripts/install-monitoring.sh 2>/dev/null || docker compose --profile monitoring up -d 2>/dev/null || true

echo ""
echo "==> Tier 2 (optional profiles)"
docker compose --profile storage up -d minio 2>/dev/null || true
bash scripts/init-minio-buckets.sh 2>/dev/null || true
docker compose --profile orchestration up -d langgraph 2>/dev/null || true
bash scripts/install-platform-crons.sh 2>/dev/null || true

echo ""
echo "==> Smoke"
bash scripts/telegram-smoke-test.sh 2>/dev/null || true

echo ""
echo "=== Bootstrap complete ==="
echo "Manual: Telegram groups, OAuth (Gmail), Traefik DNS, @mention smoke test"
echo "Verify: bash scripts/verify-platform.sh (when available)"
echo "Docs:   $DOCS/PLATFORM-DEPLOY-TEMPLATE.md"
