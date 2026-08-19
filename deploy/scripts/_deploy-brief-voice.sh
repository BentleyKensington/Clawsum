#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
ST=/tmp/clawsum-brief-voice
CONTAINER=clawsum-paperclip-1

cp -f "$ST/plugin_api.py" "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py"
cp -f "$ST/index.js" "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js"
cp -f "$ST/style.css" "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css"
cp -f "$ST/BOOT.md" "$ST/SOUL.md" "$ROOT/examples/hermes-cockpit/"

for name in clawsum-inbox clawsum-agents clawsum-skills; do
  cp -f "$ST/style.css" "$ROOT/examples/hermes-cockpit/plugin/$name/dashboard/dist/style.css" 2>/dev/null || true
done

bash "$ROOT/scripts/deploy-hermes-persona.sh"
docker cp "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py"
docker cp "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js" \
  "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"
docker cp "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css" \
  "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css"
for name in clawsum-inbox clawsum-agents clawsum-skills; do
  docker cp "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css" \
    "$CONTAINER:/paperclip/.hermes/plugins/$name/dashboard/dist/style.css" 2>/dev/null || true
done

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 2
bash "$ROOT/scripts/ensure-hermes-runtime.sh" || true

TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token")
echo "=== session-startup sample ==="
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-startup \
  | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("ok", d.get("ok"))
print("greeting_pool", len(d.get("greetings") or []))
print("progress", d.get("progress"))
print("active", len(d.get("active_tasks") or []), (d.get("active_tasks") or [])[:3])
print("upcoming", len(d.get("upcoming_tasks") or []), (d.get("upcoming_tasks") or [])[:3])
print("next", d.get("next_actions"))
print("inbox", d.get("inbox_needs_boss"))
print("voice", d.get("voice"))
'
echo DONE
