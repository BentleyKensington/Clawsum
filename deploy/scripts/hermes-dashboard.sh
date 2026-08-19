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
# Wheel installs ship TUI at hermes_cli/tui_dist/entry.js but Hermes looks for
# checkout ui-tui/ first and aborts. HERMES_TUI_DIR must contain dist/entry.js.
TUI_PREBUILT_CT="${HERMES_TUI_PREBUILT:-/paperclip/.hermes/tui-prebuilt}"
TUI_DIST_CT="${HERMES_TUI_DIST:-/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist}"

cmd="${1:-status}"

start_gateway() {
    if docker exec -u root "${CONTAINER}" bash -lc '
      export PATH=/paperclip/.hermes-venv/bin:/usr/local/bin:/usr/bin:/bin
      export HERMES_HOME=/paperclip/.hermes
      hermes gateway status 2>&1 | grep -q "Gateway is running"
    '; then
      echo gateway_already
      return 0
    fi
    docker exec -d -u root "${CONTAINER}" bash -lc '
      export PATH=/paperclip/.hermes-venv/bin:/usr/local/bin:/usr/bin:/bin
      export HERMES_HOME=/paperclip/.hermes
      mkdir -p /paperclip/logs
      exec hermes gateway run --accept-hooks >>/paperclip/logs/hermes-gateway.log 2>&1
    ' || true
    echo started_gateway
}

case "$cmd" in
  start)
    already=0
    if docker exec "${CONTAINER}" test -f "${PIDFILE}" 2>/dev/null; then
      oldpid=$(docker exec "${CONTAINER}" cat "${PIDFILE}" 2>/dev/null || true)
      if [[ -n "${oldpid}" ]] && docker exec "${CONTAINER}" kill -0 "${oldpid}" 2>/dev/null; then
        echo "Hermes dashboard already running (pid ${oldpid})"
        already=1
      fi
    fi
    if [[ "${already}" -eq 0 ]]; then
      if command -v pgrep >/dev/null 2>&1; then
        pgrep -f 'hermes dashboard' >/dev/null 2>&1 && pkill -9 -f 'hermes dashboard' || true
      fi
      docker exec -u root "${CONTAINER}" bash -lc "
        set -eu
        mkdir -p \"\$(dirname ${LOG})\" \"\$(dirname ${TOKEN_FILE_CT})\" '${TUI_PREBUILT_CT}'
        if [[ ! -s ${TOKEN_FILE_CT} ]]; then
          /paperclip/.hermes-venv/bin/python3 -c 'import secrets,pathlib; pathlib.Path(\"${TOKEN_FILE_CT}\").write_text(secrets.token_urlsafe(32))'
        fi
        if [[ ! -f '${TUI_DIST_CT}/entry.js' ]]; then
          echo 'FATAL: bundled TUI missing at ${TUI_DIST_CT}/entry.js' >&2
          exit 1
        fi
        ln -sfn '${TUI_DIST_CT}' '${TUI_PREBUILT_CT}/dist'
        TOKEN=\$(tr -d '\\r\\n' < ${TOKEN_FILE_CT})
        export PATH=/paperclip/.hermes-venv/bin:\$PATH
        export HERMES_DASHBOARD_SESSION_TOKEN=\"\$TOKEN\"
        export HERMES_TUI_DIR='${TUI_PREBUILT_CT}'
        export HERMES_HOME=/paperclip/.hermes
        nohup env \
          HERMES_DASHBOARD_SESSION_TOKEN=\"\$TOKEN\" \
          HERMES_TUI_DIR='${TUI_PREBUILT_CT}' \
          HERMES_HOME=/paperclip/.hermes \
          PATH=/paperclip/.hermes-venv/bin:\$PATH \
          ${HERMES_BIN} dashboard --host ${HOST} --port ${PORT} --no-open \
          >>\"${LOG}\" 2>&1 &
        echo \$! > \"${PIDFILE}\"
      "
      sleep 2
      if curl -sf "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
        echo "OK Hermes dashboard http://${HOST}:${PORT} (HERMES_TUI_DIR=${TUI_PREBUILT_CT})"
      else
        echo "Started (check log): docker exec ${CONTAINER} tail -30 ${LOG}"
        exit 1
      fi
    fi
    start_gateway
    ;;
  gateway)
    start_gateway
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
    if docker exec -u root "${CONTAINER}" bash -lc '
      export PATH=/paperclip/.hermes-venv/bin:/usr/local/bin:/usr/bin:/bin
      export HERMES_HOME=/paperclip/.hermes
      hermes gateway status 2>&1 | grep -q "Gateway is running"
    '; then
      echo "OK Hermes gateway running"
    else
      echo "Hermes gateway not running"
    fi
    ;;
  logs)
    docker exec "${CONTAINER}" tail -f "${LOG}"
    ;;
  *)
    echo "Usage: $0 {start|stop|status|logs|gateway}"
    exit 1
    ;;
esac
