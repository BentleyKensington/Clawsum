#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
P=/paperclip/.hermes/plugins/clawsum-cockpit/dashboard
mkdir -p "$D/dist/vendor"
cp -f /tmp/index.js "$D/dist/index.js"
cp -f /tmp/style.css "$D/dist/style.css"
cp -f /tmp/manifest.json "$D/manifest.json"
cp -f /tmp/plugin_api.py "$D/plugin_api.py"

V="$D/dist/vendor"
if [ ! -s "$V/three.min.js" ]; then
  curl -fsSL "https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js" -o "$V/three.min.js" \
    || curl -fsSL "https://unpkg.com/three@0.160.1/build/three.min.js" -o "$V/three.min.js"
fi
if [ ! -s "$V/3d-force-graph.min.js" ]; then
  curl -fsSL "https://cdn.jsdelivr.net/npm/3d-force-graph@1.73.3/dist/3d-force-graph.min.js" -o "$V/3d-force-graph.min.js" \
    || curl -fsSL "https://unpkg.com/3d-force-graph@1.73.3/dist/3d-force-graph.min.js" -o "$V/3d-force-graph.min.js"
fi

docker exec -u root clawsum-paperclip-1 bash -lc "mkdir -p $P/dist/vendor"
docker cp /tmp/index.js clawsum-paperclip-1:$P/dist/index.js
docker cp /tmp/style.css clawsum-paperclip-1:$P/dist/style.css
docker cp /tmp/manifest.json clawsum-paperclip-1:$P/manifest.json
docker cp /tmp/plugin_api.py clawsum-paperclip-1:$P/plugin_api.py
docker cp "$V/three.min.js" clawsum-paperclip-1:$P/dist/vendor/three.min.js
docker cp "$V/3d-force-graph.min.js" clawsum-paperclip-1:$P/dist/vendor/3d-force-graph.min.js

bash "$R/scripts/hermes-dashboard.sh" stop || true
docker exec -u root clawsum-paperclip-1 bash -lc 'rm -f /paperclip/logs/hermes-dashboard.pid' || true
sleep 1
bash "$R/scripts/hermes-dashboard.sh" start
sleep 2
echo CANVAS_GRAPH_APPLIED
ls -la "$V"
curl -fsS -o /dev/null -w "vendor-three:%{http_code}\n" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/vendor/three.min.js || true
curl -fsS -o /dev/null -w "vendor-fg:%{http_code}\n" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/vendor/3d-force-graph.min.js || true
