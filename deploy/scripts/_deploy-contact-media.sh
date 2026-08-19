#!/usr/bin/env bash
# Deploy contact upsert + Arcade mirror + MinIO attachment archive.
set -euo pipefail
ST=/tmp/clawsum-contact-media
ROOT=/docker/clawsum
SCR="$ROOT/scripts"

set -a
set +u
# shellcheck disable=SC1091
. "$ROOT/.env" || true
set -u
set +a

cp -f "$ST/17-ops-media-graph.sql" "$ROOT/postgres-init/"
for f in clawsum_contacts.py clawsum_arcade.py minio_store.py gmail-sync.py gmail-inbox-review.py init-minio-buckets.sh; do
  cp -f "$ST/$f" "$SCR/$f"
  sed -i 's/\r$//' "$SCR/$f"
done
sed -i 's/\r$//' "$ROOT/postgres-init/17-ops-media-graph.sql"
chmod +x "$SCR/init-minio-buckets.sh" "$SCR/gmail-sync.py"

echo "=== apply SQL ==="
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" \
  < "$ROOT/postgres-init/17-ops-media-graph.sql"

echo "=== minio buckets ==="
bash "$SCR/init-minio-buckets.sh" || true

echo "=== ensure minio python ==="
pip3 install --break-system-packages -q minio 2>/dev/null || true

echo "=== smoke contact upsert ==="
cd "$SCR"
python3 <<'PY'
import os, sys
sys.path.insert(0, "/docker/clawsum/scripts")
import psycopg2, psycopg2.extras
from clawsum_contacts import upsert_person, extract_contacts_from_text

env = {}
for line in open("/docker/clawsum/.env"):
    line=line.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    k,_,v=line.partition("=")
    env[k.strip()]=v.strip().strip('"').strip("'")

conn = psycopg2.connect(
    host=env.get("POSTGRES_HOST","127.0.0.1"),
    port=int(env.get("POSTGRES_PORT","5432")),
    dbname=env.get("POSTGRES_DB","clawsum"),
    user=env.get("POSTGRES_USER","clawsum"),
    password=env.get("POSTGRES_PASSWORD",""),
)
with conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        r1 = upsert_person(
            cur,
            display_name="Smoke Test Contact",
            emails=["smoke.contact@clawsum.test"],
            phones=["3125550199"],
            tags=["smoke"],
            source="smoke",
            notes="pipeline smoke",
        )
        r2 = upsert_person(
            cur,
            display_name="Smoke Test Contact Updated",
            emails=["smoke.contact@clawsum.test", "smoke.alt@clawsum.test"],
            phones=["3125550199"],
            tags=["smoke", "merged"],
            source="smoke",
        )
        print("created", r1.get("created"), "id", r1.get("id"))
        print("merged", not r2.get("created"), "emails", r2.get("emails"), "phones", r2.get("phones"))
        assert r1["id"] == r2["id"], "upsert should merge same email"
        assert "smoke.alt@clawsum.test" in (r2.get("emails") or [])
        ex = extract_contacts_from_text("Call Jane at 312-555-0100 or jane@example.com")
        print("extract", ex)
print("contact smoke OK")
PY

echo "=== arcade smoke (best-effort) ==="
python3 <<'PY'
import sys
sys.path.insert(0, "/docker/clawsum/scripts")
try:
    from clawsum_arcade import mirror_person
    mirror_person({
        "id": "00000000-0000-0000-0000-000000000001",
        "display_name": "Arcade Smoke",
        "emails": ["arcade.smoke@clawsum.test"],
        "phones": [],
    })
    print("arcade smoke OK")
except Exception as e:
    print("arcade smoke WARN:", e)
PY

echo "=== minio smoke ==="
python3 <<'PY'
import sys
sys.path.insert(0, "/docker/clawsum/scripts")
try:
    import minio_store
    up = minio_store.upload_bytes(
        b"clawsum-smoke-bytes",
        bucket="clawsum-attachments",
        object_key="smoke/contact-media.txt",
        content_type="text/plain",
        filename="contact-media.txt",
    )
    print("minio smoke OK", up["uri"], up["sha256"][:12])
except Exception as e:
    print("minio smoke WARN:", e)
PY

echo "DONE — next incremental gmail sync will upsert contacts + archive attachments"
echo "  GMAIL_INCREMENTAL_QUERY='newer_than:1d' python3 $SCR/gmail-sync.py"
