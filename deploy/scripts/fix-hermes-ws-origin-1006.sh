#!/usr/bin/env bash
# Fix Hermes WS close 1006: origin_mismatch behind Traefik + stable session token.
set -euo pipefail

TRAEFIK_YML=/docker/traefik/dynamic/clawsum-com.yml
TOKEN_FILE=/docker/clawsum/paperclip-data/.hermes/dashboard-session.token
CONTAINER=clawsum-paperclip-1

echo "== Traefik: rewrite Host + Origin for Hermes =="
python3 - <<'PY'
from pathlib import Path
p = Path("/docker/traefik/dynamic/clawsum-com.yml")
t = p.read_text()
old = '''    hermes-host-rewrite:
      headers:
        customRequestHeaders:
          Host: "127.0.0.1:9119"
'''
new = '''    hermes-host-rewrite:
      headers:
        customRequestHeaders:
          # Loopback Host so Hermes Host-guard passes (DNS rebinding defence).
          Host: "127.0.0.1:9119"
          # Browser Origin is https://hermes.clawsum.com — Hermes WS rejects that
          # as origin_mismatch (close 1006). Rewrite to loopback so PTY works
          # behind Traefik while Traefik basic-auth remains the outer gate.
          Origin: "http://127.0.0.1:9119"
'''
if "Origin: \"http://127.0.0.1:9119\"" in t or "Origin: 'http://127.0.0.1:9119'" in t:
    print("Origin rewrite already present")
elif old in t:
    p.write_text(t.replace(old, new, 1))
    print("patched hermes-host-rewrite")
else:
    # try looser match
    import re
    pat = re.compile(
        r"    hermes-host-rewrite:\n      headers:\n        customRequestHeaders:\n          Host: \"127\.0\.0\.1:9119\"\n",
        re.M,
    )
    if not pat.search(t):
        raise SystemExit("hermes-host-rewrite block not found — edit clawsum-com.yml manually")
    p.write_text(pat.sub(new, t, count=1))
    print("patched hermes-host-rewrite (regex)")
PY

# Ensure router still uses the middleware
grep -A12 'clawsum-hermes:' "$TRAEFIK_YML" | head -20

echo "== stable HERMES_DASHBOARD_SESSION_TOKEN =="
mkdir -p "$(dirname "$TOKEN_FILE")"
if [[ ! -s "$TOKEN_FILE" ]]; then
  python3 - <<'PY'
import secrets
from pathlib import Path
Path("/docker/clawsum/paperclip-data/.hermes/dashboard-session.token").write_text(secrets.token_urlsafe(32))
print("generated token file")
PY
fi
TOKEN=$(tr -d '\r\n' < "$TOKEN_FILE")
# also copy into container hermes home
docker cp "$TOKEN_FILE" "$CONTAINER:/paperclip/.hermes/dashboard-session.token"

echo "== rewrite hermes-dashboard.sh start with token + full hermes path =="
cat > /docker/clawsum/scripts/hermes-dashboard.sh <<'EOF'
#!/usr/bin/env bash
# Start/stop/status Hermes web dashboard (127.0.0.1:9119) in Paperclip container.
set -eu

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
PORT="${HERMES_DASHBOARD_PORT:-9119}"
HOST="${HERMES_DASHBOARD_HOST:-127.0.0.1}"
LOG="${HERMES_DASHBOARD_LOG:-/paperclip/logs/hermes-dashboard.log}"
PIDFILE="${HERMES_DASHBOARD_PIDFILE:-/paperclip/logs/hermes-dashboard.pid}"
HERMES_BIN="${HERMES_BIN:-/paperclip/.hermes-venv/bin/hermes}"
TOKEN_FILE_CT="${HERMES_TOKEN_FILE:-/paperclip/.hermes/dashboard-session.token}"

cmd="${1:-status}"

case "$cmd" in
  start)
    if docker exec "${CONTAINER}" test -f "${PIDFILE}" 2>/dev/null; then
      oldpid=$(docker exec "${CONTAINER}" cat "${PIDFILE}" 2>/dev/null || true)
      if [[ -n "${oldpid}" ]] && docker exec "${CONTAINER}" kill -0 "${oldpid}" 2>/dev/null; then
        echo "Hermes dashboard already running (pid ${oldpid})"
        exit 0
      fi
    fi
    # Host-visible stale processes (docker host networking / pid visibility)
    if command -v pgrep >/dev/null 2>&1; then
      pgrep -f 'hermes dashboard' >/dev/null 2>&1 && pkill -9 -f 'hermes dashboard' || true
    fi
    docker exec -u root "${CONTAINER}" bash -lc "
      set -eu
      mkdir -p \"\$(dirname ${LOG})\" \"\$(dirname ${TOKEN_FILE_CT})\"
      if [[ ! -s ${TOKEN_FILE_CT} ]]; then
        /paperclip/.hermes-venv/bin/python3 -c 'import secrets,pathlib; pathlib.Path(\"${TOKEN_FILE_CT}\").write_text(secrets.token_urlsafe(32))'
      fi
      TOKEN=\$(tr -d '\\r\\n' < ${TOKEN_FILE_CT})
      export HERMES_DASHBOARD_SESSION_TOKEN=\"\$TOKEN\"
      export PATH=/paperclip/.hermes-venv/bin:\$PATH
      nohup env HERMES_DASHBOARD_SESSION_TOKEN=\"\$TOKEN\" \
        ${HERMES_BIN} dashboard --host ${HOST} --port ${PORT} --no-open \
        >>\"${LOG}\" 2>&1 &
      echo \$! > \"${PIDFILE}\"
    "
    sleep 2
    if curl -sf "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
      echo "OK Hermes dashboard http://${HOST}:${PORT}"
    else
      echo "Started (check log): docker exec ${CONTAINER} tail -30 ${LOG}"
      exit 1
    fi
    ;;
  stop)
    if command -v pgrep >/dev/null 2>&1; then
      pkill -9 -f 'hermes dashboard' 2>/dev/null || true
    fi
    docker exec "${CONTAINER}" bash -lc "
      if [[ -f ${PIDFILE} ]]; then
        kill \"\$(cat ${PIDFILE})\" 2>/dev/null || true
        rm -f ${PIDFILE}
      fi
    " || true
    echo "Hermes dashboard stopped"
    ;;
  status)
    if curl -sf "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
      echo "OK Hermes dashboard listening on ${HOST}:${PORT}"
    else
      echo "Hermes dashboard not responding on ${PORT}"
      exit 1
    fi
    ;;
  logs)
    docker exec "${CONTAINER}" tail -f "${LOG}"
    ;;
  *)
    echo "Usage: $0 {start|stop|status|logs}"
    exit 1
    ;;
esac
EOF
chmod +x /docker/clawsum/scripts/hermes-dashboard.sh

echo "== reload traefik + restart hermes =="
# Traefik file provider watches; bounce for certainty
docker restart traefik-traefik-1 >/dev/null 2>&1 || docker restart "$(docker ps --format '{{.Names}}' | grep -i traefik | head -1)" || true
sleep 3

bash /docker/clawsum/scripts/hermes-dashboard.sh stop || true
sleep 1
bash /docker/clawsum/scripts/hermes-dashboard.sh start

echo "== verify middleware =="
grep -A8 'hermes-host-rewrite:' "$TRAEFIK_YML"
echo DONE
echo "Boss: hard-refresh https://hermes.clawsum.com (Ctrl+Shift+R) — WS 1006 should clear."
