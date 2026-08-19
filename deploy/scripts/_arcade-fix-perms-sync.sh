#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
PASS=$(grep '^ARCADEDB_ROOT_PASSWORD=' "$ROOT/.env" | cut -d= -f2- | tr -d '"' | tr -d "'")
cd "$ROOT"

# Fix volume ownership for ArcadeDB process user
docker compose stop arcadedb || true
mkdir -p data/arcadedb
# Arcade image typically runs as uid 999 or arcadedb user — make writable
chmod -R a+rwX data/arcadedb || true
chown -R 999:999 data/arcadedb 2>/dev/null || chown -R 1000:1000 data/arcadedb 2>/dev/null || true
docker compose up -d arcadedb
sleep 8

AUTH=(-u "root:${PASS}" -H 'Content-Type: application/json')
echo "=== ready ==="
curl -sS -m 5 "${AUTH[@]}" http://127.0.0.1:2480/api/v1/ready; echo
echo "=== create database ==="
curl -sS -m 20 "${AUTH[@]}" -d '{"command":"create database clawsum_graph"}' http://127.0.0.1:2480/api/v1/server; echo
echo "=== list ==="
curl -sS -m 10 "${AUTH[@]}" -d '{"command":"list databases"}' http://127.0.0.1:2480/api/v1/server; echo

cp -f /tmp/clawsum-contact-media/clawsum_arcade.py "$ROOT/scripts/" 2>/dev/null || true
sed -i 's/\r$//' "$ROOT/scripts/clawsum_arcade.py"

python3 <<'PY'
import sys
sys.path.insert(0, "/docker/clawsum/scripts")
import clawsum_arcade as a
a._READY = False
from clawsum_arcade import mirror_person, link_mentioned, _cmd
mirror_person({
    "id": "00000000-0000-0000-0000-000000000001",
    "display_name": "Arcade Smoke",
    "emails": ["arcade.smoke@clawsum.test"],
    "phones": [],
})
mirror_person({
    "id": "00000000-0000-0000-0000-000000000002",
    "display_name": "Arcade Smoke 2",
    "emails": ["arcade2@clawsum.test"],
    "phones": [],
})
link_mentioned(
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
)
print("person rows", _cmd("SELECT count(*) as c FROM Person"))
print("arcade OK")
PY

export GMAIL_INCREMENTAL_QUERY='newer_than:6h'
timeout 180 python3 "$ROOT/scripts/gmail-sync.py" 2>&1 | tail -50

set -a; set +u; . "$ROOT/.env"; set -u; set +a
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" <<'SQL'
SELECT count(*) AS people FROM ops.people;
SELECT count(*) AS media FROM ops.media_objects;
SELECT count(*) AS emails_with_att FROM ops.emails WHERE jsonb_array_length(COALESCE(attachments,'[]'::jsonb)) > 0;
SELECT display_name, primary_email, phones FROM ops.people ORDER BY updated_at DESC NULLS LAST LIMIT 8;
SQL
echo DONE
