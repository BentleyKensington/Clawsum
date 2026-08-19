#!/usr/bin/env bash
# Keep Hermes dashboard (:9119) AND messaging gateway alive.
# Idempotent. Safe for cron every 2 minutes and systemd After=docker.
set -u
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
LOCK="${CLAWSUM_HERMES_LOCK:-/var/lock/clawsum-hermes-runtime.lock}"
TUI_PREBUILT=/paperclip/.hermes/tui-prebuilt
TUI_DIST=/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist
PATH_CT=/paperclip/.hermes-venv/bin:/usr/local/bin:/usr/bin:/bin

mkdir -p "$(dirname "$LOCK")" /var/log
exec 9>"$LOCK"
if ! flock -n 9; then
  exit 0
fi

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; then
  echo "paperclip_down"
  exit 0
fi

# Repair a corrupt config.yaml from the last known-good snapshot.
if [[ -f "$ROOT/scripts/hermes-config-safe.py" ]]; then
  python3 "$ROOT/scripts/hermes-config-safe.py" --repair \
    --path "$ROOT/paperclip-data/.hermes/config.yaml" || true
fi

# TUI symlink (required for /chat PTY)
docker exec -u root "$CONTAINER" bash -lc "
  mkdir -p ${TUI_PREBUILT}
  if [[ -f ${TUI_DIST}/entry.js ]]; then
    ln -sfn ${TUI_DIST} ${TUI_PREBUILT}/dist
  fi
" || true

bash "$ROOT/scripts/hermes-dashboard.sh" status >/dev/null 2>&1 \
  || bash "$ROOT/scripts/hermes-dashboard.sh" start || true

# Dashboard start used to exit early and skip the gateway. Always assert it.
if docker exec -u root "$CONTAINER" bash -lc "
  export PATH=${PATH_CT}
  export HERMES_HOME=/paperclip/.hermes
  hermes gateway status 2>&1 | grep -q 'Gateway is running'
"; then
  echo gateway_ok
else
  docker exec -d -u root "$CONTAINER" bash -lc "
    export PATH=${PATH_CT}
    export HERMES_HOME=/paperclip/.hermes
    mkdir -p /paperclip/logs
    exec hermes gateway run --accept-hooks >>/paperclip/logs/hermes-gateway.log 2>&1
  " || true
  echo started_gateway
  sleep 2
fi

python3 - <<'PY'
import json, pathlib, urllib.request
up = 0
sessions = 0
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:9119/api/status", timeout=4))
    up = 1 if d.get("gateway_running") else 0
    sessions = int(d.get("active_sessions") or 0)
    print("dashboard_ok gateway_running=%s sessions=%s" % (d.get("gateway_running"), sessions))
except Exception as exc:
    print("dashboard_status_fail", exc)
tf = pathlib.Path("/docker/clawsum/data/prometheus-textfile/hermes_gateway.prom")
try:
    tf.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# HELP clawsum_hermes_gateway_up Hermes messaging gateway process\n"
        "# TYPE clawsum_hermes_gateway_up gauge\n"
        "clawsum_hermes_gateway_up %d\n"
        "# HELP clawsum_hermes_active_sessions Hermes sessions active in last 5m\n"
        "# TYPE clawsum_hermes_active_sessions gauge\n"
        "clawsum_hermes_active_sessions %d\n"
    ) % (up, sessions)
    tmp = tf.with_suffix(".prom.tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(tf)
except Exception as exc:
    print("textfile_fail", exc)
PY
