#!/usr/bin/env bash
# Deploy document chunk ETL (Postgres + MinIO + Arcade) and smoke-test.
set -euo pipefail
ST=/tmp/clawsum-docs-etl
ROOT=/docker/clawsum

cp -f "$ST/18-ops-documents.sql" "$ROOT/postgres-init/"
for f in clawsum_docs_etl.py clawsum_arcade.py; do
  cp -f "$ST/$f" "$ROOT/scripts/$f"
  sed -i 's/\r$//' "$ROOT/scripts/$f"
done
sed -i 's/\r$//' "$ROOT/postgres-init/18-ops-documents.sql"
if [[ -f "$ST/DATA-ARCADEDB-VS-POSTGRES.md" ]]; then
  mkdir -p "$ROOT/docs"
  cp -f "$ST/DATA-ARCADEDB-VS-POSTGRES.md" "$ROOT/docs/"
  sed -i 's/\r$//' "$ROOT/docs/DATA-ARCADEDB-VS-POSTGRES.md"
fi

set -a
set +u
# shellcheck disable=SC1091
. "$ROOT/.env" || true
set -u
set +a

echo "=== SQL ==="
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" \
  < "$ROOT/postgres-init/18-ops-documents.sql"

echo "=== smoke text ingest ==="
cd "$ROOT/scripts"
python3 clawsum_docs_etl.py \
  --title "ETL smoke meeting note" \
  --source upload \
  --source-ref smoke-docs-etl \
  --text "Met Jane Doe (jane.doe@acme-smoke.test) at 312-555-0142 about Deepstar and Closebot. Follow up Friday."

echo "=== postgres counts ==="
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" <<'SQL'
SELECT count(*) AS documents FROM ops.documents;
SELECT count(*) AS chunks FROM ops.document_chunks;
SELECT title, uri IS NOT NULL AS has_uri, cardinality(person_ids) AS people
FROM ops.documents ORDER BY created_at DESC LIMIT 3;
SELECT left(text, 80) AS chunk_preview FROM ops.document_chunks ORDER BY created_at DESC LIMIT 2;
SQL

echo "=== arcade counts ==="
python3 <<'PY'
import sys
sys.path.insert(0, "/docker/clawsum/scripts")
import clawsum_arcade as a
a._READY = False
from clawsum_arcade import _cmd
print("Document", _cmd("SELECT count(*) as c FROM Document"))
print("SourceChunk", _cmd("SELECT count(*) as c FROM SourceChunk"))
print("Person", _cmd("SELECT count(*) as c FROM Person"))
print("sample Document", _cmd("SELECT title, uri FROM Document LIMIT 3"))
PY

echo "=== call smoke (synthetic wav) ==="
python3 <<'PY'
from pathlib import Path
# Minimal RIFF/WAV header + silence-ish bytes (not a real recording — archive path test)
wav = Path("/tmp/clawsum-smoke-call.wav")
# 44-byte header for 8-bit mono PCM + 100 samples
import struct
data = b"\x00" * 100
hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack(
    "<IHHIIHH", 16, 1, 1, 8000, 8000, 1, 8
) + b"data" + struct.pack("<I", len(data)) + data
wav.write_bytes(hdr)
print("wrote", wav, len(hdr), "bytes")
PY
python3 clawsum_docs_etl.py \
  --call-wav /tmp/clawsum-smoke-call.wav \
  --call-transcript "Caller John (john.smoke@clawsum.test) at 773-555-0199 asked about Hennessey Farms." \
  --caller-phone 7735550199 \
  --caller-name "John Smoke" \
  --title "Smoke inbound call"

docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "SELECT count(*) AS calls FROM ops.call_recordings; SELECT title FROM ops.call_recordings ORDER BY created_at DESC LIMIT 2;"

echo DONE
