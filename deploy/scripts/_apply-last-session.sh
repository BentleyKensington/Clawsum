#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit"
P=/paperclip/.hermes
cp -f /tmp/LAST_SESSION.md "$D/LAST_SESSION.md"
cp -f /tmp/LAST_SESSION.md "$R/paperclip-data/.hermes/LAST_SESSION.md"
cp -f /tmp/plugin_api.py "$D/plugin/clawsum-cockpit/dashboard/plugin_api.py"
docker cp /tmp/LAST_SESSION.md clawsum-paperclip-1:$P/LAST_SESSION.md
docker cp /tmp/plugin_api.py clawsum-paperclip-1:$P/plugins/clawsum-cockpit/dashboard/plugin_api.py
bash "$R/scripts/hermes-dashboard.sh" stop || true
docker exec -u root clawsum-paperclip-1 bash -lc 'rm -f /paperclip/logs/hermes-dashboard.pid' || true
sleep 1
bash "$R/scripts/hermes-dashboard.sh" start
echo LAST_SESSION_APPLIED
head -8 "$R/paperclip-data/.hermes/LAST_SESSION.md"
