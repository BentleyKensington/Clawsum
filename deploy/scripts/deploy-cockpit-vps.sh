#!/bin/bash
# Deploy Clawsum cockpit / overwatch / cron fixes on the reference VPS.
# Run on VPS as root from /tmp or after sync.
set -euo pipefail
ROOT=/docker/clawsum
cd "$ROOT"

echo "==> Layout check"
ls scripts/install-hermes-cockpit.sh
ls examples/hermes-cockpit/theme/clawsum-command.yaml || ls deploy/examples/hermes-cockpit/theme/clawsum-command.yaml

echo "==> Fix daily report cron (7am America/Chicago)"
bash scripts/install-daily-report-cron.sh || true
bash scripts/install-reminders-cron.sh || true
bash scripts/install-obsidian-sync-cron.sh || true
echo "--- crontab ---"
crontab -l | head -30

echo "==> Overwatch schema"
SQL=""
if [[ -f postgres-init/12-overwatch.sql ]]; then
  SQL=postgres-init/12-overwatch.sql
elif [[ -f deploy/postgres-init/12-overwatch.sql ]]; then
  SQL=deploy/postgres-init/12-overwatch.sql
fi
if [[ -n "$SQL" ]]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
  docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" < "$SQL" || \
    psql "postgresql://${POSTGRES_USER:-clawsum}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB:-clawsum}" -f "$SQL" || true
fi

echo "==> Seed business cells"
python3 scripts/seed-business-cells.py || pip3 install -q psycopg2-binary && python3 scripts/seed-business-cells.py

echo "==> Hermes dashboard + cockpit"
bash scripts/install-hermes-dashboard.sh || true
bash scripts/hermes-dashboard.sh stop || true
bash scripts/install-hermes-cockpit.sh
bash scripts/hermes-dashboard.sh start || true
bash scripts/hermes-dashboard.sh status || true

echo "==> Done"
echo "Open Hermes UI (tunnel or hermes host), pick theme Clawsum Command, open Clawsum tab."
