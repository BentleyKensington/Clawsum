#!/bin/bash
# Provision GHL account agent(s) from templates/ghl/ + ghl-accounts.json
set -euo pipefail
cd /docker/clawsum

mkdir -p config templates/ghl
if [[ -d /docker/clawsum/deploy/config ]]; then
  cp -f deploy/config/ghl-accounts.json config/ghl-accounts.json 2>/dev/null || true
fi
if [[ -d /docker/clawsum/deploy/templates/ghl ]]; then
  cp -rf deploy/templates/ghl/* templates/ghl/ 2>/dev/null || true
elif [[ -d /docker/clawsum/deploy/templates/ghl-account ]]; then
  mkdir -p templates/ghl-account
  cp -rf deploy/templates/ghl-account/* templates/ghl-account/ 2>/dev/null || true
fi

python3 scripts/provision-ghl-accounts.py "$@"
python3 scripts/verify-ghl-isolation.py

echo ""
echo "Next: cd /docker/clawsum && docker compose restart openclaw-gateway"
echo "When Boss provides PIT + locationId, add to .env and re-run this script."
