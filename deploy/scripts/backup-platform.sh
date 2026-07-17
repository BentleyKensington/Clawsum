#!/bin/bash
# Nightly platform backup: Postgres dumps + Obsidian tarball → data/backups (and MinIO when configured).
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"
STAMP=$(date +%Y%m%d-%H%M)
DEST="data/backups/${STAMP}"
mkdir -p "$DEST"

set -a
set +u
# shellcheck disable=SC1091
source .env 2>/dev/null || true
set -u
set +a

PG_USER="${POSTGRES_USER:-clawsum}"
for db in clawsum ghl realestate; do
  docker exec clawsum-postgres-1 pg_dump -U "$PG_USER" -Fc "$db" > "${DEST}/${db}.dump" 2>/dev/null \
    && echo "OK dump ${db}" || echo "SKIP dump ${db}"
done

if [[ -d obsidian ]]; then
  tar -czf "${DEST}/obsidian.tgz" -C . obsidian
  echo "OK obsidian.tgz"
fi

if docker compose --profile storage ps --status running 2>/dev/null | grep -q minio; then
  USER="${MINIO_ROOT_USER:-clawsum}"
  PASS="${MINIO_ROOT_PASSWORD:-minio_change_me}"
  docker run --rm --network host --entrypoint /bin/sh \
    -v "${ROOT}/${DEST}:/backup:ro" \
    minio/mc:latest \
    -c "mc alias set local http://127.0.0.1:9000 ${USER} ${PASS} && mc cp -r /backup local/clawsum-backups/${STAMP}/" \
    2>/dev/null && echo "OK MinIO upload ${STAMP}" || echo "WARN MinIO upload failed"
fi

find data/backups -maxdepth 1 -type d -mtime +14 -exec rm -rf {} + 2>/dev/null || true
echo "Backup complete: ${DEST}"
