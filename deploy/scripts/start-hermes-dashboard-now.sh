#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 tail -40 /paperclip/logs/hermes-dashboard.log || true
echo "--- start ---"
docker exec -u root clawsum-paperclip-1 bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  mkdir -p /paperclip/logs
  rm -f /paperclip/logs/hermes-dashboard.pid
  nohup hermes dashboard --host 127.0.0.1 --port 9119 --no-open >>/paperclip/logs/hermes-dashboard.log 2>&1 &
  echo $! > /paperclip/logs/hermes-dashboard.pid
  echo pid=$(cat /paperclip/logs/hermes-dashboard.pid)
'
sleep 4
curl -sS -o /tmp/hs.json -w "http:%{http_code}\n" http://127.0.0.1:9119/api/status || true
head -c 200 /tmp/hs.json; echo
pgrep -af 'hermes dashboard' || true
docker exec clawsum-paperclip-1 tail -20 /paperclip/logs/hermes-dashboard.log || true
