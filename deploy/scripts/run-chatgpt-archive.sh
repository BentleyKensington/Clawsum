#!/usr/bin/env bash
# Run ChatGPT archive pipeline: schema (optional) → import → classify → link → brief.
# Usage:
#   bash run-chatgpt-archive.sh /path/to/export.zip
#   bash run-chatgpt-archive.sh /path/to/conversations.json --skip-schema
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SCRIPTS="${ROOT}/scripts"
if [[ ! -d "$SCRIPTS" ]]; then
  SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
  ROOT="$(cd "${SCRIPTS}/.." && pwd)"
fi
INIT="${ROOT}/postgres-init"
if [[ ! -d "$INIT" ]]; then
  INIT="${ROOT}/deploy/postgres-init"
fi

EXPORT="${1:-}"
SKIP_SCHEMA=0
shift || true
for arg in "$@"; do
  case "$arg" in
    --skip-schema) SKIP_SCHEMA=1 ;;
  esac
done

if [[ -z "$EXPORT" ]]; then
  echo "Usage: $0 /path/to/chatgpt-export.zip [--skip-schema]" >&2
  exit 1
fi
if [[ ! -f "$EXPORT" ]]; then
  echo "ERROR: export not found: $EXPORT" >&2
  exit 1
fi

# shellcheck disable=SC1091
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

if [[ "$SKIP_SCHEMA" -eq 0 ]]; then
  echo "== schema 13-chatgpt-archive =="
  psql -h "$PGHOST" -U "$PGUSER" -d "$PGDB" -v ON_ERROR_STOP=1 -f "${INIT}/13-chatgpt-archive.sql"
fi

echo "== import =="
python3 "${SCRIPTS}/import-chatgpt-export.py" "$EXPORT"

echo "== classify (personal | business + questions) =="
python3 "${SCRIPTS}/classify-chatgpt-archive.py"

echo "== link Paperclip =="
python3 "${SCRIPTS}/link-archive-to-paperclip.py"

echo "== proactive brief =="
python3 "${SCRIPTS}/archive-proactive-brief.py" --markdown

echo ""
echo "OK. Hermes SOUL: examples/hermes-cockpit/SOUL.md (re-run install-hermes-cockpit.sh to install)."
echo "Doc: docs/CHATGPT-ARCHIVE.md"
