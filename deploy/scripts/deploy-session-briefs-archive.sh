#!/usr/bin/env bash
# Deploy session-briefs archive (SQL + cockpit API/UI + persona).
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${ROOT}/examples/hermes-cockpit"
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
PG_CONTAINER="${POSTGRES_CONTAINER:-clawsum-postgres-1}"

echo "=== apply 15-session-briefs.sql ==="
docker cp "${ROOT}/postgres-init/15-session-briefs.sql" "${PG_CONTAINER}:/tmp/15-session-briefs.sql"
cd "$ROOT"
set +u
set -a
# shellcheck disable=SC1091
. ./.env
set +a
docker exec -i "$PG_CONTAINER" \
  env PGPASSWORD="${POSTGRES_PASSWORD}" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -v ON_ERROR_STOP=1 \
  -f /tmp/15-session-briefs.sql

echo "=== sync cockpit plugin into examples tree (already on host) + container ==="
mkdir -p "${ROOT}/paperclip-data/.hermes/session-briefs"
echo "# Session Startup Briefs archive" > "${ROOT}/paperclip-data/.hermes/session-briefs/README.md"
docker exec -u root "$CONTAINER" mkdir -p /paperclip/.hermes/session-briefs
docker cp "${ROOT}/paperclip-data/.hermes/session-briefs/README.md" \
  "$CONTAINER:/paperclip/.hermes/session-briefs/README.md" || true

bash "${ROOT}/scripts/deploy-hermes-persona.sh"
bash "${ROOT}/scripts/redeploy-hermes-cockpit-ui.sh"

echo "=== seed one test brief via API (localhost dashboard) ==="
sleep 2
curl -sS -X POST "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-briefs" \
  -H "Content-Type: application/json" \
  -d '{"greeting":"Archive wiring check","body_md":"# Session Startup Brief\n\nArchive wiring check.\n\n## Last session\nnot enough data — seed entry.\n\n## Next actions\n1. Open Boss → Archive and confirm this brief appears.\n","source":"manual"}' \
  | head -c 800 || true
echo
curl -sS "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-briefs?limit=3" | head -c 1200 || true
echo
echo DONE
