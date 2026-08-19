#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
mkdir -p "$D/dist" "$R/scripts" "$R/paperclip-data/.hermes"
cp -f /tmp/graphify_views.py "$D/graphify_views.py"
cp -f /tmp/plugin_api.py "$D/plugin_api.py"
cp -f /tmp/manifest.json "$D/manifest.json"
cp -f /tmp/index.js "$D/dist/index.js"
cp -f /tmp/style.css "$D/dist/style.css"
cp -f /tmp/snapshot-obsidian-graph.py "$R/scripts/snapshot-obsidian-graph.py"
sed -i 's/\r$//' "$R/scripts/snapshot-obsidian-graph.py" "$R/scripts/redeploy-hermes-cockpit-ui.sh"
python3 -m py_compile "$D/graphify_views.py" "$D/plugin_api.py"
python3 "$R/scripts/snapshot-obsidian-graph.py" || echo SNAPSHOT_SKIP
bash "$R/scripts/redeploy-hermes-cockpit-ui.sh"
# Also drop snapshot into the live plugin home in case paperclip home differs
if [[ -f "$R/paperclip-data/.hermes/obsidian-graph.json" ]]; then
  docker exec -u root clawsum-paperclip-1 mkdir -p /paperclip/.hermes || true
  docker cp "$R/paperclip-data/.hermes/obsidian-graph.json" clawsum-paperclip-1:/paperclip/.hermes/obsidian-graph.json || true
fi
echo GRAPH_DECK_APPLIED
