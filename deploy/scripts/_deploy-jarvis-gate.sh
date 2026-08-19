#!/usr/bin/env bash
set -euo pipefail
ST=/tmp/clawsum-jarvis-gate
ROOT=/docker/clawsum
C=clawsum-paperclip-1
EX="$ROOT/examples/hermes-cockpit"

# SQL (idempotent create + mode constraint includes boss_ordered)
cp -f "$ST/16-jarvis-processes.sql" "$ROOT/postgres-init/"
sed -i 's/\r$//' "$ROOT/postgres-init/16-jarvis-processes.sql"
set -a
set +u
# shellcheck disable=SC1091
. "$ROOT/.env" || true
set -u
set +a
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" \
  < "$ROOT/postgres-init/16-jarvis-processes.sql"

# Ensure mode constraint allows boss_ordered (for DBs created before that value)
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" <<'SQL'
ALTER TABLE ops.jarvis_processes DROP CONSTRAINT IF EXISTS jarvis_processes_mode_chk;
ALTER TABLE ops.jarvis_processes
  ADD CONSTRAINT jarvis_processes_mode_chk
  CHECK (mode IN ('plan_gate', 'preapproved_fast', 'boss_ordered'));

-- Gerald already ordered the 9-agent batch — no second Approve
UPDATE ops.jarvis_processes
SET status = 'confirmed',
    mode = 'boss_ordered',
    approved_at = COALESCE(approved_at, now()),
    updated_at = now(),
    meta = COALESCE(meta, '{}'::jsonb) || '{"source":"boss_order","note":"Boss ordered in chat — pre-authorized"}'::jsonb
WHERE title = 'Create 9 agents (Hennessey batch)'
  AND status IN ('proposed', 'confirmed');
SQL

# Persona + UI
for f in SOUL.md WORKFLOWS.md BOOT.md; do
  cp -f "$ST/$f" "$EX/$f"
  sed -i 's/\r$//' "$EX/$f"
  docker cp "$EX/$f" "$C:/paperclip/.hermes/$f"
  cp -f "$EX/$f" "$ROOT/paperclip-data/.hermes/$f" 2>/dev/null || true
done
cp -f "$ST/plugin_api.py" "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py"
cp -f "$ST/index.js" "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
sed -i 's/\r$//' "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js" \
  "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"
if [[ -f "$ST/style.css" ]]; then
  cp -f "$ST/style.css" "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css"
  sed -i 's/\r$//' "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css"
  docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css" \
    "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css"
fi
if [[ -f "$ST/AUTHORITY.md" ]]; then
  mkdir -p "$ROOT/skills" "$EX/../../skills" 2>/dev/null || true
  cp -f "$ST/AUTHORITY.md" "$ROOT/skills/AUTHORITY.md" 2>/dev/null || true
  sed -i 's/\r$//' "$ROOT/skills/AUTHORITY.md" 2>/dev/null || true
fi

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 3
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
echo "=== kpi ==="
curl -sS -H "X-Hermes-Session-Token: ${TOKEN}" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/processes/kpi | head -c 600; echo
echo "=== session-startup insight ==="
curl -sS -H "X-Hermes-Session-Token: ${TOKEN}" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-startup \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print("ok",d.get("ok")); print("insight_md_len",len(d.get("insight_md") or "")); print("awaiting", (d.get("jarvis") or {}).get("awaiting_boss")); print((d.get("insight_md") or "")[:400])'
echo "=== processes head ==="
curl -sS -H "X-Hermes-Session-Token: ${TOKEN}" \
  "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/processes?limit=3" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print([(p.get("title"),p.get("status"),p.get("mode")) for p in (d.get("processes") or [])[:3]])'
echo DONE
