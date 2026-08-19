#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
mkdir -p "$D/dist" "$R/examples/hermes-cockpit/skins"
cp -f /tmp/index.js "$D/dist/index.js"
cp -f /tmp/style.css "$D/dist/style.css"
cp -f /tmp/manifest.json "$D/manifest.json"
cp -f /tmp/clawsum.yaml "$R/examples/hermes-cockpit/skins/clawsum.yaml"
docker cp /tmp/index.js clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
docker cp /tmp/style.css clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css
docker cp /tmp/manifest.json clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/manifest.json
docker cp /tmp/clawsum.yaml clawsum-paperclip-1:/paperclip/.hermes/skins/clawsum.yaml
echo CHAT_CLEAN_APPLIED
