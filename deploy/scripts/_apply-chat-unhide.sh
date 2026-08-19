#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
mkdir -p "$D/dist"
cp -f /tmp/index.js "$D/dist/index.js"
cp -f /tmp/style.css "$D/dist/style.css"
cp -f /tmp/manifest.json "$D/manifest.json"
docker cp /tmp/index.js clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
docker cp /tmp/style.css clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css
docker cp /tmp/manifest.json clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/manifest.json
bash "$R/scripts/hermes-dashboard.sh" stop || true
docker exec -u root clawsum-paperclip-1 bash -lc 'rm -f /paperclip/logs/hermes-dashboard.pid' || true
sleep 1
bash "$R/scripts/hermes-dashboard.sh" start
echo CHAT_UNHIDE_APPLIED
