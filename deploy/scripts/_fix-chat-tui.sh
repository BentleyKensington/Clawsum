#!/usr/bin/env bash
# Fix Chat unavailable: point Hermes at wheel-bundled TUI and restart dashboard.
set -euo pipefail
ROOT=/docker/clawsum
CONTAINER=clawsum-paperclip-1
TUI_PREBUILT=/paperclip/.hermes/tui-prebuilt
TUI_DIST=/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist

cp -f /tmp/fix-chat-tui/hermes-dashboard.sh "$ROOT/scripts/hermes-dashboard.sh"
chmod +x "$ROOT/scripts/hermes-dashboard.sh"
dos2unix "$ROOT/scripts/hermes-dashboard.sh" 2>/dev/null || true

echo "=== wire HERMES_TUI_DIR prebuilt layout ==="
docker exec -u root "$CONTAINER" bash -lc "
  set -e
  test -f ${TUI_DIST}/entry.js
  mkdir -p ${TUI_PREBUILT}
  ln -sfn ${TUI_DIST} ${TUI_PREBUILT}/dist
  ls -la ${TUI_PREBUILT}/dist/entry.js
"

# Prove argv resolution works with env set
docker exec -u root "$CONTAINER" bash -lc "
  export PATH=/paperclip/.hermes-venv/bin:\$PATH
  export HERMES_TUI_DIR=${TUI_PREBUILT}
  /paperclip/.hermes-venv/bin/python3 - <<'PY'
from pathlib import Path
from hermes_cli.main import _make_tui_argv, PROJECT_ROOT
argv, cwd = _make_tui_argv(PROJECT_ROOT / 'ui-tui', tui_dev=False)
print('argv', argv)
print('cwd', cwd)
assert Path(argv[-1]).is_file(), argv[-1]
print('TUI_OK')
PY
"

echo "=== restart dashboard with TUI env ==="
bash "$ROOT/scripts/force-restart-hermes-dashboard.sh" || bash "$ROOT/scripts/hermes-dashboard.sh start"
sleep 3

# ensure gateway still up
bash "$ROOT/scripts/ensure-hermes-runtime.sh" 2>/dev/null || true

echo "=== verify env on running dashboard ==="
PID=$(docker exec "$CONTAINER" cat /paperclip/logs/hermes-dashboard.pid)
docker exec "$CONTAINER" bash -lc "tr '\\0' '\\n' </proc/${PID}/environ | grep -E 'HERMES_TUI_DIR|HERMES_DASHBOARD_SESSION' | sed 's/=.*/=***/'"

echo "=== recent dashboard log (should NOT say ui-tui missing) ==="
docker exec "$CONTAINER" tail -30 /paperclip/logs/hermes-dashboard.log | grep -iE 'ui-tui|TUI|HERMES_DASHBOARD_READY|unavailable|error' || true
docker exec "$CONTAINER" tail -8 /paperclip/logs/hermes-dashboard.log

echo "=== websocket smoke (pty) ==="
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
docker exec -u root "$CONTAINER" bash -lc "
  export PATH=/paperclip/.hermes-venv/bin:\$PATH
  /paperclip/.hermes-venv/bin/python3 - <<PY
import asyncio, json, os
try:
    import websockets
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'websockets'])
    import websockets

TOKEN = '''${TOKEN}'''

async def main():
    uri = 'ws://127.0.0.1:9119/api/pty?token=' + TOKEN
    headers = {'X-Hermes-Session-Token': TOKEN, 'Origin': 'http://127.0.0.1:9119'}
    try:
        async with websockets.connect(uri, additional_headers=headers, open_timeout=8) as ws:
            # read a couple frames / text
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3)
                except asyncio.TimeoutError:
                    print('TIMEOUT_WAITING_FRAME')
                    break
                if isinstance(msg, bytes):
                    print('BIN', len(msg))
                else:
                    s = msg[:200].replace('\\n','\\\\n')
                    print('TXT', s)
                    if 'Chat unavailable' in msg:
                        print('FAIL_STILL_UNAVAILABLE')
                        return
            print('PTY_WS_OK')
    except Exception as e:
        print('PTY_WS_ERR', type(e).__name__, e)

asyncio.run(main())
PY
"

echo DONE
