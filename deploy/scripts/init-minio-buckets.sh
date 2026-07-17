#!/bin/bash
# Create default MinIO buckets for Clawsum (storage profile).
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"

if ! docker compose --profile storage ps --status running 2>/dev/null | grep -q minio; then
  echo "SKIP MinIO buckets — minio not running (docker compose --profile storage up -d minio)"
  exit 0
fi

set -a
# shellcheck disable=SC1091
set +u
source .env 2>/dev/null || true
set -u
set +a

USER="${MINIO_ROOT_USER:-clawsum}"
PASS="${MINIO_ROOT_PASSWORD:-minio_change_me}"
ENDPOINT="http://127.0.0.1:9000"

for bucket in clawsum-attachments clawsum-scrapes clawsum-backups; do
  docker run --rm --network host --entrypoint /bin/sh \
    minio/mc:latest \
    -c "mc alias set local ${ENDPOINT} ${USER} ${PASS} && mc mb -p local/${bucket} 2>/dev/null || mc ls local/${bucket}" \
    && echo "OK bucket ${bucket}"
done
