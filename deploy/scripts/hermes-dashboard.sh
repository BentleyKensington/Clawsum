#!/usr/bin/env bash
# Start/stop/status Hermes web dashboard (127.0.0.1:9119) in Paperclip container.
set -eu

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
PORT="${HERMES_DASHBOARD_PORT:-9119}"
HOST="${HERMES_DASHBOARD_HOST:-127.0.0.1}"
LOG="${HERMES_DASHBOARD_LOG:-/paperclip/logs/hermes-dashboard.log}"
PIDFILE="${HERMES_DASHBOARD_PIDFILE:-/paperclip/logs/hermes-dashboard.pid}"

cmd="${1:-status}"

case "$cmd" in
  start)
    if docker exec "${CONTAINER}" test -f "${PIDFILE}" 2>/dev/null \
      && docker exec "${CONTAINER}" kill -0 "$(docker exec "${CONTAINER}" cat "${PIDFILE}")" 2>/dev/null; then
      echo "Hermes dashboard already running (pid $(docker exec "${CONTAINER}" cat "${PIDFILE}"))"
      exit 0
    fi
    docker exec -u root "${CONTAINER}" bash -lc "
      set -eu
      mkdir -p \"$(dirname "${LOG}")\"
      nohup hermes dashboard --host ${HOST} --port ${PORT} --no-open \
        >>\"${LOG}\" 2>&1 &
      echo \$! > \"${PIDFILE}\"
    "
    sleep 2
    if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null 2>&1 || curl -sf "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
      echo "OK Hermes dashboard http://${HOST}:${PORT}"
    else
      echo "Started (check log): docker exec ${CONTAINER} tail -30 ${LOG}"
    fi
    ;;
  stop)
    docker exec "${CONTAINER}" bash -lc "
      if [[ -f ${PIDFILE} ]]; then
        kill \"\$(cat ${PIDFILE})\" 2>/dev/null || true
        rm -f ${PIDFILE}
      fi
      pkill -f 'hermes dashboard' 2>/dev/null || true
    " || true
    echo "Hermes dashboard stopped"
    ;;
  status)
    if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null 2>&1 || curl -sf "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
      echo "OK Hermes dashboard listening on ${HOST}:${PORT}"
    else
      echo "Hermes dashboard not responding on ${PORT}"
      docker exec "${CONTAINER}" test -f "${LOG}" 2>/dev/null \
        && docker exec "${CONTAINER}" tail -5 "${LOG}" 2>/dev/null || true
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
