#!/usr/bin/env bash
set -euo pipefail
PASS=$(grep '^ARCADEDB_ROOT_PASSWORD=' /docker/clawsum/.env | cut -d= -f2- | tr -d '"' | tr -d "'")
AUTH=(-u "root:${PASS}" -H 'Content-Type: application/json')
echo "=== ready ==="
curl -sS -m 5 "${AUTH[@]}" http://127.0.0.1:2480/api/v1/ready; echo
echo "=== list databases ==="
curl -sS -m 10 "${AUTH[@]}" -d '{"command":"list databases"}' http://127.0.0.1:2480/api/v1/server; echo
echo "=== create database ==="
curl -sS -m 15 "${AUTH[@]}" -d '{"command":"create database clawsum_graph if not exists"}' http://127.0.0.1:2480/api/v1/server; echo
echo "=== select ==="
curl -sS -m 10 "${AUTH[@]}" -d '{"language":"sql","command":"SELECT 1 as ok"}' \
  http://127.0.0.1:2480/api/v1/command/clawsum_graph; echo
python3 <<'PY'
import sys
sys.path.insert(0, "/docker/clawsum/scripts")
# force re-init
import clawsum_arcade as a
a._READY = False
from clawsum_arcade import mirror_person, link_mentioned, _cmd
print(_cmd("SELECT FROM `Person` LIMIT 1"))
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
print("arcade person count", _cmd("SELECT count(*) as c FROM `Person`"))
print("arcade OK")
PY
export GMAIL_INCREMENTAL_QUERY='newer_than:6h'
timeout 180 python3 /docker/clawsum/scripts/gmail-sync.py 2>&1 | tail -40
set -a; set +u; . /docker/clawsum/.env; set -u; set +a
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" <<'SQL'
SELECT count(*) AS people FROM ops.people;
SELECT count(*) AS media FROM ops.media_objects;
SELECT count(*) AS emails_with_att FROM ops.emails WHERE jsonb_array_length(COALESCE(attachments,'[]'::jsonb)) > 0;
SELECT display_name, primary_email, phones[1] AS phone FROM ops.people ORDER BY updated_at DESC NULLS LAST LIMIT 8;
SQL
