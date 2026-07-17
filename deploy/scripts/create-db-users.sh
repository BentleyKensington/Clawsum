#!/bin/bash
# Apply separate RE/GHL databases on existing Postgres (init only runs once)
set -euo pipefail

pg() { docker exec clawsum-postgres-1 psql -U clawsum -d postgres -v ON_ERROR_STOP=1 "$@"; }

echo "==> Creating separate databases for realestate and ghl..."
pg -tc "SELECT 1 FROM pg_database WHERE datname='realestate'" | grep -q 1 || \
  pg -c "CREATE DATABASE realestate;"
pg -tc "SELECT 1 FROM pg_database WHERE datname='ghl'" | grep -q 1 || \
  pg -c "CREATE DATABASE ghl;"

docker exec -i clawsum-postgres-1 psql -U clawsum -d realestate -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA IF NOT EXISTS deals;
CREATE SCHEMA IF NOT EXISTS listings;
CREATE SCHEMA IF NOT EXISTS contacts;
SQL

docker exec -i clawsum-postgres-1 psql -U clawsum -d ghl -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA IF NOT EXISTS pipelines;
CREATE SCHEMA IF NOT EXISTS contacts;
CREATE SCHEMA IF NOT EXISTS campaigns;
SQL

SQL_FILE="/docker/clawsum/postgres-init/07-ghl-account-schemas.sql"
if [[ -f "$SQL_FILE" ]]; then
  echo "==> Applying GHL per-account schemas/roles..."
  docker exec -i clawsum-postgres-1 psql -U clawsum -d ghl -v ON_ERROR_STOP=1 < "$SQL_FILE"
fi

echo "==> Done. Main DB 'clawsum' keeps ops/coding/data/comms/research/planning schemas."
