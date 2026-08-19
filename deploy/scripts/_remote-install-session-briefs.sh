#!/usr/bin/env bash
# Install session-briefs archive files already staged under /tmp/clawsum-briefs
set -euo pipefail
STAGING=/tmp/clawsum-briefs
ROOT=/docker/clawsum
CONTAINER=clawsum-paperclip-1

cp -f "$STAGING/15-session-briefs.sql" "$ROOT/postgres-init/"
cp -f "$STAGING/deploy-session-briefs-archive.sh" "$ROOT/scripts/"
cp -f "$STAGING/deploy-hermes-persona.sh" "$ROOT/scripts/"
cp -f "$STAGING/redeploy-hermes-cockpit-ui.sh" "$ROOT/scripts/" 2>/dev/null || true
chmod +x "$ROOT/scripts/"*.sh

# Persona into examples tree
cp -f "$STAGING/BOOT.md" "$STAGING/SOUL.md" "$STAGING/WORKFLOWS.md" \
  "$ROOT/examples/hermes-cockpit/"

# Plugin API + UI into examples tree
cp -f "$STAGING/plugin/dashboard/plugin_api.py" \
  "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py"
cp -f "$STAGING/plugin/dashboard/index.js" \
  "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js"

# CRLF hygiene
command -v dos2unix >/dev/null 2>&1 && dos2unix \
  "$ROOT/postgres-init/15-session-briefs.sql" \
  "$ROOT/scripts/deploy-session-briefs-archive.sh" \
  "$ROOT/scripts/deploy-hermes-persona.sh" \
  "$ROOT/examples/hermes-cockpit/BOOT.md" \
  "$ROOT/examples/hermes-cockpit/SOUL.md" \
  "$ROOT/examples/hermes-cockpit/WORKFLOWS.md" \
  "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  2>/dev/null || true

echo "=== apply SQL ==="
cd "$ROOT"
set +u
set -a
# shellcheck disable=SC1091
. ./.env
set +a
set -u
docker exec -i clawsum-postgres-1 \
  env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -v ON_ERROR_STOP=1 \
  < postgres-init/15-session-briefs.sql

echo "=== session-briefs dir ==="
mkdir -p "$ROOT/paperclip-data/.hermes/session-briefs"
printf '%s\n' '# Session Startup Briefs' 'Archived Hermes BOOT.md first messages.' \
  > "$ROOT/paperclip-data/.hermes/session-briefs/README.md"
docker exec -u root "$CONTAINER" mkdir -p /paperclip/.hermes/session-briefs
docker cp "$ROOT/paperclip-data/.hermes/session-briefs/README.md" \
  "$CONTAINER:/paperclip/.hermes/session-briefs/README.md"

echo "=== persona + UI ==="
bash "$ROOT/scripts/deploy-hermes-persona.sh"
bash "$ROOT/scripts/redeploy-hermes-cockpit-ui.sh"

sleep 3
echo "=== POST seed brief ==="
curl -sS -X POST "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-briefs" \
  -H "Content-Type: application/json" \
  -d '{"greeting":"Archive wiring check","body_md":"# Session Startup Brief\n\nArchive wiring check.\n\n## Last session\nnot enough data — seed entry.\n\n## Next actions\n1. Open Boss → Archive and confirm this brief appears.\n","source":"manual"}' || true
echo
echo "=== LIST ==="
curl -sS "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-briefs?limit=3" || true
echo
echo DONE
