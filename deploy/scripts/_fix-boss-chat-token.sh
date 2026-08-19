#!/usr/bin/env bash
set +u
set -eo pipefail
CONTAINER=clawsum-paperclip-1
HOST_H=/docker/clawsum/paperclip-data/.hermes

echo "=== token files ==="
ls -la "$HOST_H/dashboard-session.token" 2>/dev/null || echo "no host token"
docker exec "$CONTAINER" ls -la /paperclip/.hermes/dashboard-session.token /paperclip/logs/hermes-dashboard.pid 2>&1 || true
docker exec "$CONTAINER" bash -lc 'echo HERMES_DASHBOARD_SESSION_TOKEN_len=${#HERMES_DASHBOARD_SESSION_TOKEN}; tr "\\0" "\\n" </proc/1/environ 2>/dev/null | grep -i hermes | head; ls /proc/*/cmdline 2>/dev/null | head'
# find dashboard process env
PID=$(docker exec "$CONTAINER" cat /paperclip/logs/hermes-dashboard.pid 2>/dev/null || true)
echo "pidfile=$PID"
if [[ -n "$PID" ]]; then
  docker exec "$CONTAINER" bash -lc "tr '\\0' '\\n' </proc/$PID/environ 2>/dev/null | grep -E 'HERMES|TOKEN|HOME' | sed 's/=.*/=***/'" || true
  docker exec "$CONTAINER" bash -lc "tr '\\0' ' ' </proc/$PID/cmdline; echo" || true
fi

echo "=== recreate token + restart dashboard properly ==="
mkdir -p "$HOST_H"
if [[ ! -s "$HOST_H/dashboard-session.token" ]]; then
  python3 -c 'import secrets; open("/docker/clawsum/paperclip-data/.hermes/dashboard-session.token","w").write(secrets.token_urlsafe(32))'
  echo generated_host_token
fi
TOKEN=$(tr -d '\r\n' < "$HOST_H/dashboard-session.token")
echo "token_len=${#TOKEN}"
docker exec -u root "$CONTAINER" mkdir -p /paperclip/.hermes /paperclip/logs
docker cp "$HOST_H/dashboard-session.token" "$CONTAINER:/paperclip/.hermes/dashboard-session.token"

# Kill existing dashboard cleanly
bash /docker/clawsum/scripts/force-restart-hermes-dashboard.sh || bash /docker/clawsum/scripts/hermes-dashboard.sh start
sleep 3

echo "=== probe with Bearer + X header ==="
for hdr in "Authorization: Bearer $TOKEN" "X-Hermes-Session-Token: $TOKEN"; do
  echo "HDR=$hdr"
  curl -sS -o /tmp/cp.json -w "code:%{http_code}\n" -H "$hdr" \
    http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-briefs?limit=2 || true
  head -c 350 /tmp/cp.json; echo
done

echo "=== status after restart ==="
curl -sS http://127.0.0.1:9119/api/status | python3 -c 'import sys,json; d=json.load(sys.stdin); print({k:d[k] for k in ("version","config_version","latest_config_version","gateway_running","auth_required","active_sessions")})'

echo "=== start messaging gateway in background ==="
docker exec -u root "$CONTAINER" bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  export HERMES_HOME=/paperclip/.hermes
  mkdir -p /paperclip/logs
  if ! hermes gateway status 2>&1 | grep -q "Gateway is running"; then
    nohup hermes gateway run --accept-hooks >>/paperclip/logs/hermes-gateway.log 2>&1 &
    echo $! > /paperclip/logs/hermes-gateway.pid
    echo started_gateway pid=$(cat /paperclip/logs/hermes-gateway.pid)
  else
    echo gateway_already
  fi
'
sleep 4
docker exec "$CONTAINER" bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes gateway status 2>&1 | head -20'
curl -sS http://127.0.0.1:9119/api/status | python3 -c 'import sys,json; d=json.load(sys.stdin); print("gateway_running", d.get("gateway_running"), "platforms", d.get("gateway_platforms"))'
tail -30 /docker/clawsum/paperclip-data/logs/hermes-gateway.log 2>/dev/null || docker exec "$CONTAINER" tail -30 /paperclip/logs/hermes-gateway.log 2>/dev/null || true
