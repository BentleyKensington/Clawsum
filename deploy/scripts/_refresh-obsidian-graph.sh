#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
cp -f /tmp/graphify_views.py "$D/graphify_views.py"
docker cp /tmp/graphify_views.py clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/graphify_views.py
python3 "$R/scripts/snapshot-obsidian-graph.py"
docker exec -u root clawsum-paperclip-1 mkdir -p /paperclip/.hermes
docker cp "$R/paperclip-data/.hermes/obsidian-graph.json" clawsum-paperclip-1:/paperclip/.hermes/obsidian-graph.json
echo OBSIDIAN_REFRESHED
