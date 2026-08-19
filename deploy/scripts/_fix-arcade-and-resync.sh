#!/usr/bin/env bash
set -euo pipefail
ST=/tmp/clawsum-contact-media
ROOT=/docker/clawsum
cp -f "$ST/gmail-sync.py" "$ROOT/scripts/"
cp -f "$ST/clawsum_arcade.py" "$ROOT/scripts/"
cp -f "$ST/docker-compose.yml" "$ROOT/"
sed -i 's/\r$//' "$ROOT/scripts/gmail-sync.py" "$ROOT/scripts/clawsum_arcade.py" "$ROOT/docker-compose.yml"

cd "$ROOT"
if ! grep -q '^ARCADEDB_ROOT_PASSWORD=' .env; then
  echo "ARCADEDB_ROOT_PASSWORD=clawsum_arcade_$(openssl rand -hex 4)" >> .env
fi
PASS=$(grep '^ARCADEDB_ROOT_PASSWORD=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")

docker compose up -d arcadedb
sleep 6

ready() {
  curl -sf -m 5 -u "root:${PASS}" http://127.0.0.1:2480/api/v1/ready >/dev/null 2>&1
}

if ! ready; then
  echo "Arcade not ready — reset data volume and recreate with JAVA_OPTS password"
  docker compose stop arcadedb || true
  docker compose rm -f arcadedb || true
  rm -rf "$ROOT/data/arcadedb"/*
  mkdir -p "$ROOT/data/arcadedb"
  docker compose up -d arcadedb
  sleep 10
fi

echo "=== arcade ready? ==="
if ready; then
  echo YES
else
  echo NO
  docker logs clawsum-arcadedb-1 --tail 40 || true
fi

python3 <<'PY'
import sys
sys.path.insert(0, "/docker/clawsum/scripts")
from clawsum_arcade import mirror_person, link_mentioned
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
print("arcade OK")
PY

echo "=== gmail sync (6h) ==="
export GMAIL_INCREMENTAL_QUERY='newer_than:6h'
timeout 180 python3 "$ROOT/scripts/gmail-sync.py" 2>&1 | tail -60

echo "=== counts ==="
set -a; set +u; . "$ROOT/.env"; set -u; set +a
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "SELECT count(*) AS people FROM ops.people; SELECT count(*) AS media FROM ops.media_objects; SELECT count(*) AS emails_with_att FROM ops.emails WHERE jsonb_array_length(COALESCE(attachments,'[]'::jsonb)) > 0;"
echo DONE
