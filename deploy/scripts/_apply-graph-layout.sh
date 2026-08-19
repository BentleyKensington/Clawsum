#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
P=/paperclip/.hermes/plugins/clawsum-cockpit/dashboard
cp -f /tmp/index.js "$D/dist/index.js"
cp -f /tmp/style.css "$D/dist/style.css"
docker cp /tmp/index.js clawsum-paperclip-1:$P/dist/index.js
docker cp /tmp/style.css clawsum-paperclip-1:$P/dist/style.css
bash "$R/scripts/hermes-dashboard.sh" stop || true
docker exec -u root clawsum-paperclip-1 bash -lc 'rm -f /paperclip/logs/hermes-dashboard.pid' || true
sleep 1
bash "$R/scripts/hermes-dashboard.sh" start
echo GRAPH_LAYOUT_APPLIED
