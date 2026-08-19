#!/usr/bin/env bash
set -euo pipefail
export GMAIL_INCREMENTAL_QUERY='newer_than:2d'
timeout 240 python3 /docker/clawsum/scripts/gmail-sync.py
set -a; set +u; . /docker/clawsum/.env; set -u; set +a
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "SELECT count(*) AS people FROM ops.people; SELECT count(*) AS media FROM ops.media_objects; SELECT count(*) AS with_att FROM ops.emails WHERE jsonb_array_length(COALESCE(attachments,'[]'::jsonb))>0;"
