#!/usr/bin/env bash
# Seed CRM layer + optionally review clawsums@gmail.com inbox.
# Usage:
#   bash run-overwatch-crm.sh
#   bash run-overwatch-crm.sh --review-inbox
#   bash run-overwatch-crm.sh --review-inbox --sync-first
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SCRIPTS="${ROOT}/scripts"
if [[ ! -d "$SCRIPTS" ]]; then
  SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
  ROOT="$(cd "${SCRIPTS}/.." && pwd)"
fi
INIT="${ROOT}/postgres-init"
[[ -d "$INIT" ]] || INIT="${ROOT}/deploy/postgres-init"

REVIEW=0
SYNC_FIRST=0
for arg in "$@"; do
  case "$arg" in
    --review-inbox) REVIEW=1 ;;
    --sync-first) SYNC_FIRST=1 ;;
  esac
done

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT}/.env"
  set +a
fi

export PGPASSWORD="${POSTGRES_PASSWORD:-}"
PGHOST="${POSTGRES_HOST:-127.0.0.1}"
PGUSER="${POSTGRES_USER:-clawsum}"
PGDB="${POSTGRES_DB:-clawsum}"

echo "== schema 14-ops-crm =="
psql -h "$PGHOST" -U "$PGUSER" -d "$PGDB" -v ON_ERROR_STOP=1 -f "${INIT}/14-ops-crm.sql"

echo "== seed cells =="
python3 "${SCRIPTS}/seed-business-cells.py"

echo "== seed people + places =="
python3 "${SCRIPTS}/seed-people-places.py"

if [[ "$REVIEW" -eq 1 ]]; then
  echo "== inbox review clawsums@gmail.com =="
  EXTRA=()
  [[ "$SYNC_FIRST" -eq 1 ]] && EXTRA+=(--sync-first)
  python3 "${SCRIPTS}/gmail-inbox-review.py" --inbox-only --markdown --create-reminders "${EXTRA[@]}"
fi

echo "OK. Docs: docs/OVERWATCH-CRM.md"
