#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
ST=/tmp/clawsum-dock
CONTAINER=clawsum-paperclip-1

cp -f "$ST/plugin_api.py" "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py"
cp -f "$ST/index.js" "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js"
cp -f "$ST/style.css" "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css"
cp -f "$ST/BOOT.md" "$ST/SOUL.md" "$ROOT/examples/hermes-cockpit/"

# sync CSS to sibling plugins
for name in clawsum-inbox clawsum-agents clawsum-skills; do
  cp -f "$ST/style.css" "$ROOT/examples/hermes-cockpit/plugin/$name/dashboard/dist/style.css" 2>/dev/null || true
done

bash "$ROOT/scripts/deploy-hermes-persona.sh"
bash "$ROOT/scripts/install-clawsum-sidebar-plugins.sh"
bash "$ROOT/scripts/force-restart-hermes-dashboard.sh" || bash "$ROOT/scripts/hermes-dashboard.sh start"
sleep 2
bash "$ROOT/scripts/ensure-hermes-runtime.sh" || true

TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
echo "=== session-startup ==="
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-startup \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("ok",d.get("ok"),"greetings",len(d.get("greetings") or []),"suggestions",len(d.get("suggestions") or []),"report",d.get("report")); print("last", (d.get("last_session") or "")[:120])'

echo "=== markers in plugin ==="
docker exec "$CONTAINER" grep -c 'clawsum-chat-frame\|session-startup\|isEmbeddedFrame' \
  /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
docker exec "$CONTAINER" grep -c 'clawsum-dock-h\|chatdock-frame' \
  /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css
echo DONE
