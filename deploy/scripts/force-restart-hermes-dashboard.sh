#!/usr/bin/env bash
set -euo pipefail
CONTAINER=clawsum-paperclip-1
# Kill by pid from host (process is visible on host with docker)
PIDS=$(pgrep -f 'hermes dashboard' || true)
if [[ -n "${PIDS}" ]]; then
  echo "killing: $PIDS"
  kill -9 $PIDS || true
fi
docker exec -u root "$CONTAINER" bash -lc 'rm -f /paperclip/logs/hermes-dashboard.pid; command -v pkill >/dev/null && pkill -9 -f "hermes dashboard" || true' || true
sleep 1
bash /docker/clawsum/scripts/hermes-dashboard.sh start
sleep 2
pgrep -af 'hermes dashboard' || true
curl -sS -o /dev/null -w "status:%{http_code}\n" http://127.0.0.1:9119/api/status
