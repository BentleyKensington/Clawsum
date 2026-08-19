#!/usr/bin/env bash
set +u
set -eo pipefail
CONTAINER=clawsum-paperclip-1

echo "=== Chat unavailable message context ==="
docker exec "$CONTAINER" python3 - <<'PY'
from pathlib import Path
p=Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py')
lines=p.read_text().splitlines()
for start in (12580, 12620, 12660, 12690):
    print(f'\n----- {start} -----')
    for i in range(start-1, min(len(lines), start+45)):
        print(f'{i+1}:{lines[i]}')
PY

echo "=== find ui-tui references ==="
docker exec "$CONTAINER" bash -lc '
  rg -n "ui-tui|UI_TUI|tui_workspace|TUI workspace" \
    /paperclip/.hermes-venv/lib/python3.13/site-packages -g "*.py" | head -40
  echo ---
  ls /paperclip/.hermes-venv/lib/python3.13/site-packages | rg -i "tui|hermes|nous" | head
  echo ---
  find /paperclip -maxdepth 4 -type d -name "ui-tui" 2>/dev/null | head
  find / -maxdepth 5 -type d -name "ui-tui" 2>/dev/null | head
'

echo "=== hermes package meta / how installed ==="
docker exec "$CONTAINER" bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  pip show hermes-agent 2>/dev/null | head -20 || pip show hermes 2>/dev/null | head -20
  hermes version 2>&1 | head -20
  hermes doctor 2>&1 | head -60
'
