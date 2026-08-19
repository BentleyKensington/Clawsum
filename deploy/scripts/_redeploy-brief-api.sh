#!/usr/bin/env bash
set -euo pipefail
docker cp /docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py \
  clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py
bash /docker/clawsum/scripts/force-restart-hermes-dashboard.sh
sleep 2
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/brief | python3 -m json.tool | head -60
echo ---
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-startup \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("report:");
[print("-",x) for x in (d.get("report") or [])]'
