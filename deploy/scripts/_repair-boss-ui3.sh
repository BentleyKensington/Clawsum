#!/usr/bin/env bash
set +u
set -eo pipefail
ROOT=/docker/clawsum
cd "$ROOT"
set -a; . ./.env; set +a

echo "=== why conversations missing ==="
ls -la postgres-init/13-chatgpt-archive.sql postgres-init/12-overwatch.sql postgres-init/14-ops-crm.sql 2>&1 | head
docker exec -i clawsum-postgres-1 env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -v ON_ERROR_STOP=1 \
  < postgres-init/13-chatgpt-archive.sql 2>&1 | tail -40

echo "=== tables now ==="
docker exec -i clawsum-postgres-1 env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "SELECT to_regclass('ops.conversations') AS conversations, to_regclass('ops.businesses') AS businesses, to_regclass('ops.session_briefs') AS briefs;"

# sync index + css into container (no self-cp)
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
echo "=== archive ==="
curl -sS -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/archive \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("ok",d.get("ok"),"briefs",d.get("session_briefs_count"),"drive",len(d.get("drive_forward") or []), "err",d.get("error"))'
echo "=== plugin markers ==="
docker exec clawsum-paperclip-1 grep -c 'Session Startup Briefs' /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
docker exec clawsum-paperclip-1 grep -c 'min-width: 11rem' /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css
echo DONE
