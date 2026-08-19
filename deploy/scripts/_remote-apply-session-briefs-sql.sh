#!/usr/bin/env bash
set +u
set -eo pipefail
cd /docker/clawsum
set -a
# shellcheck disable=SC1091
. ./.env
set +a
docker exec -i clawsum-postgres-1 \
  env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -v ON_ERROR_STOP=1 \
  < postgres-init/15-session-briefs.sql
echo SQL_OK
