#!/usr/bin/env bash
set -euo pipefail
ST=/tmp/clawsum-batch-gate
ROOT=/docker/clawsum
C=clawsum-paperclip-1
EX="$ROOT/examples/hermes-cockpit"

cp -f "$ST/16-jarvis-processes.sql" "$ROOT/postgres-init/"
sed -i 's/\r$//' "$ROOT/postgres-init/16-jarvis-processes.sql"
set -a; set +u; . "$ROOT/.env" || true; set -u; set +a
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" <<'SQL'
ALTER TABLE ops.jarvis_processes DROP CONSTRAINT IF EXISTS jarvis_processes_mode_chk;
ALTER TABLE ops.jarvis_processes
  ADD CONSTRAINT jarvis_processes_mode_chk
  CHECK (mode IN ('plan_gate', 'preapproved_fast', 'boss_ordered', 'batch_gate'));
SQL

for f in SOUL.md WORKFLOWS.md; do
  cp -f "$ST/$f" "$EX/$f"
  sed -i 's/\r$//' "$EX/$f"
  docker cp "$EX/$f" "$C:/paperclip/.hermes/$f"
  cp -f "$EX/$f" "$ROOT/paperclip-data/.hermes/$f" 2>/dev/null || true
done
cp -f "$ST/plugin_api.py" "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py"
cp -f "$ST/index.js" "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
cp -f "$ST/style.css" "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css" 2>/dev/null || true
sed -i 's/\r$//' "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js" \
  "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"
if [[ -f "$ST/style.css" ]]; then
  sed -i 's/\r$//' "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css"
  docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css" \
    "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css"
fi
if [[ -f "$ST/AUTHORITY.md" ]]; then
  mkdir -p "$ROOT/skills" 2>/dev/null || true
  cp -f "$ST/AUTHORITY.md" "$ROOT/skills/AUTHORITY.md" 2>/dev/null || true
fi

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 3
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
H=(-H "X-Hermes-Session-Token: ${TOKEN}" -H "Content-Type: application/json")
echo "=== create batch ==="
curl -sS "${H[@]}" -d '{
  "title":"Batch gate smoke",
  "intent":"Gerald asked for a multi-step demo",
  "steps":[
    {"title":"Step A — prepare","detail":"dry run only"},
    {"title":"Step B — apply","detail":"dry run only"}
  ],
  "risk_tier":1
}' http://127.0.0.1:9119/api/plugins/clawsum-cockpit/processes | python3 -c 'import sys,json; d=json.load(sys.stdin); print("ok",d.get("ok"),"mode", (d.get("process") or {}).get("mode"),"approve_all",d.get("approve_all"),"steps",len(d.get("steps") or [])); print("hint", (d.get("hint") or "")[:120]); open("/tmp/batch-id.txt","w").write((d.get("process") or {}).get("id",""))'
echo
ID=$(cat /tmp/batch-id.txt)
echo "id=$ID"
echo "=== kpi ==="
curl -sS -H "X-Hermes-Session-Token: ${TOKEN}" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/processes/kpi; echo
echo DONE
