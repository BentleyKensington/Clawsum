#!/usr/bin/env bash
# Deploy Phase 1 memory schema + smoke-test extraction on VPS.
set -eo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
PG_CONTAINER="${POSTGRES_CONTAINER:-clawsum-postgres-1}"
C="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"

cd "$ROOT"
sed -i 's/\r$//' "$ROOT/postgres-init/19-ops-memory-graph.sql" \
  "$ROOT/scripts/memory-fact-extract.py" \
  "$ROOT/scripts/clawsum_arcade.py" 2>/dev/null || true

echo "=== apply 19-ops-memory-graph.sql ==="
docker exec -i "$PG_CONTAINER" psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" \
  -v ON_ERROR_STOP=1 < "$ROOT/postgres-init/19-ops-memory-graph.sql"

echo "=== tables ==="
docker exec -i "$PG_CONTAINER" psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "\dt ops.memory_*"

env_get() {
  local k="$1"
  grep -E "^${k}=" "$ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | sed 's/\r$//; s/^"//; s/"$//; s/^'\''//; s/'\''$//' || true
}

POSTGRES_USER=$(env_get POSTGRES_USER); POSTGRES_USER=${POSTGRES_USER:-clawsum}
POSTGRES_PASSWORD=$(env_get POSTGRES_PASSWORD)
POSTGRES_DB=$(env_get POSTGRES_DB); POSTGRES_DB=${POSTGRES_DB:-clawsum}
ARCADEDB_URL=$(env_get ARCADEDB_URL); ARCADEDB_URL=${ARCADEDB_URL:-http://127.0.0.1:2480}
ARCADEDB_DATABASE=$(env_get ARCADEDB_DATABASE); ARCADEDB_DATABASE=${ARCADEDB_DATABASE:-clawsum_graph}
ARCADEDB_USER=$(env_get ARCADEDB_USER); ARCADEDB_USER=${ARCADEDB_USER:-root}
ARCADEDB_ROOT_PASSWORD=$(env_get ARCADEDB_ROOT_PASSWORD)
OPENAI_API_KEY=$(env_get OPENAI_API_KEY)
OPENROUTER_API_KEY=$(env_get OPENROUTER_API_KEY)
MEMORY_EXTRACT_MODEL=$(env_get MEMORY_EXTRACT_MODEL)

mkdir -p "$ROOT/paperclip-data/clawsum-scripts"
cp -f "$ROOT/scripts/clawsum_arcade.py" "$ROOT/scripts/memory-fact-extract.py" \
  "$ROOT/paperclip-data/clawsum-scripts/"
if [ -f "$ROOT/scripts/llm_policy.py" ]; then
  cp -f "$ROOT/scripts/llm_policy.py" "$ROOT/paperclip-data/clawsum-scripts/"
fi
sed -i 's/\r$//' "$ROOT/paperclip-data/clawsum-scripts/"*.py

echo "=== arcade warm + smoke extract ==="
docker exec -u root \
  -e POSTGRES_HOST=127.0.0.1 \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e ARCADEDB_URL="$ARCADEDB_URL" \
  -e ARCADEDB_DATABASE="$ARCADEDB_DATABASE" \
  -e ARCADEDB_USER="$ARCADEDB_USER" \
  -e ARCADEDB_ROOT_PASSWORD="$ARCADEDB_ROOT_PASSWORD" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  -e MEMORY_EXTRACT_MODEL="$MEMORY_EXTRACT_MODEL" \
  -e CLAWSUM_SOURCE_HOST=vps \
  "$C" bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
cd /paperclip/clawsum-scripts
python3 - <<PY
import clawsum_arcade as a
a._ensure_ready()
print("arcade ready")
PY
python3 memory-fact-extract.py \
  --text "Gerald owns an RTX 4070 Super. Project AcceptAI is an autonomous commerce platform. Gerald prefers self-hosting. Nick Perry invested. Task: finish Shopify MCP. Problem: ElevenLabs quota bug." \
  --source-kind manual \
  --source-ref phase1-smoke \
  --source-agent admin
'

echo "=== counts ==="
docker exec -i "$PG_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT count(*) AS facts FROM ops.memory_facts;
   SELECT subject, predicate, object, importance, confidence FROM ops.memory_facts ORDER BY updated_at DESC LIMIT 12;
   SELECT count(*) AS episodes FROM ops.memory_episodes;
   SELECT stage, ok, stats FROM ops.memory_dream_runs ORDER BY started_at DESC LIMIT 3;"

echo "DONE phase1"
