#!/usr/bin/env bash
set +u
set -eo pipefail
cd /docker/clawsum
set -a
. ./.env
set +a

STAMP=$(date -u +%Y-%m-%d-%H%M%S)
FILE="${STAMP}-seed.md"
HOST_DIR=/docker/clawsum/paperclip-data/.hermes/session-briefs
mkdir -p "$HOST_DIR"

cat > "$HOST_DIR/$FILE" <<EOF
# Session Startup Brief — ${STAMP}Z

Archive wiring check.

## Last session
not enough data — seed entry for Gerald.

## Updates
none flagged.

## Concerns
none flagged.

## Next actions
1. Open Boss → **Archive** → Session Startup Briefs and confirm this entry.
EOF

docker exec -u root clawsum-paperclip-1 mkdir -p /paperclip/.hermes/session-briefs
docker cp "$HOST_DIR/$FILE" "clawsum-paperclip-1:/paperclip/.hermes/session-briefs/$FILE"

# Escape single quotes for SQL
BODY_ESC=$(sed "s/'/''/g" "$HOST_DIR/$FILE")

docker exec -i clawsum-postgres-1 \
  env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO ops.session_briefs (greeting, body_md, source, file_uri)
VALUES (
  'Archive wiring check',
  '${BODY_ESC}',
  'manual',
  '/paperclip/.hermes/session-briefs/${FILE}'
);
SELECT id, created_at, left(greeting,40) AS greeting, source FROM ops.session_briefs ORDER BY created_at DESC LIMIT 3;
SQL

docker exec clawsum-paperclip-1 grep -n 'session-briefs\|session_briefs' /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py | head
docker exec clawsum-paperclip-1 ls -la /paperclip/.hermes/session-briefs/
echo SEED_OK
