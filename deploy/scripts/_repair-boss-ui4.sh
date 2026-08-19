#!/usr/bin/env bash
set +u
set -eo pipefail
ROOT=/docker/clawsum
cd "$ROOT"
set -a; . ./.env; set +a

echo "=== apply 13-chatgpt-archive.sql ==="
docker exec -i clawsum-postgres-1 env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -v ON_ERROR_STOP=1 \
  < postgres-init/13-chatgpt-archive.sql

docker exec -i clawsum-postgres-1 env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "SELECT to_regclass('ops.conversations') AS conversations, to_regclass('ops.session_briefs') AS briefs;"

CSS="$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css"
JS="$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js"
API="$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py"
docker cp "$CSS" clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css
docker cp "$JS" clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
docker cp "$API" clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py
for name in clawsum-inbox clawsum-agents clawsum-skills; do
  docker cp "$CSS" "clawsum-paperclip-1:/paperclip/.hermes/plugins/$name/dashboard/dist/style.css" || true
done

bash /docker/clawsum/scripts/force-restart-hermes-dashboard.sh
sleep 2
bash /docker/clawsum/scripts/ensure-hermes-runtime.sh

TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
curl -sS -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/archive \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("archive", {k:d.get(k) for k in ("ok","session_briefs_count","personal_conversations","error")})'
curl -sS -H "X-Hermes-Session-Token: $TOKEN" -o /dev/null -w "plugin_js:%{http_code}\n" \
  http://127.0.0.1:9119/plugins/clawsum-cockpit/dist/index.js
curl -sS http://127.0.0.1:9119/api/status | python3 -c 'import sys,json;d=json.load(sys.stdin);print("gateway",d.get("gateway_running"))'
echo DONE
