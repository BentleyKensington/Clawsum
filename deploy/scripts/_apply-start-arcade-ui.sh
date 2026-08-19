#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
mkdir -p "$D/dist"
cp -f /tmp/index.js "$D/dist/index.js"
cp -f /tmp/style.css "$D/dist/style.css" 2>/dev/null || true
cp -f /tmp/manifest.json "$D/manifest.json"
cp -f /tmp/plugin_api.py "$D/plugin_api.py"
docker cp /tmp/index.js clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
docker cp /tmp/manifest.json clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/manifest.json
docker cp /tmp/plugin_api.py clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py
python3 -m py_compile "$D/plugin_api.py"
bash "$R/scripts/hermes-dashboard.sh" stop || true
docker exec -u root clawsum-paperclip-1 bash -lc 'rm -f /paperclip/logs/hermes-dashboard.pid' || true
sleep 1
bash "$R/scripts/hermes-dashboard.sh" start
echo START_ARCADE_UI_APPLIED
