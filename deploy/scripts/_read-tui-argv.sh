#!/usr/bin/env bash
set +u
docker exec clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
import re

# main.py helpers
main = Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/main.py').read_text()
for name in ('_make_tui_argv', '_ensure_tui_workspace', '_restore_tui_workspace', 'PROJECT_ROOT'):
    i = main.find(f'def {name}') if name.startswith('_') else -1
    if name == 'PROJECT_ROOT':
        for m in re.finditer(r'PROJECT_ROOT\s*=.*', main):
            print(m.group(0)[:200])
            break
        continue
    if i < 0:
        print('missing', name)
        continue
    print('\n====', name, '====')
    print(main[i:i+1800])

ws = Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py').read_text()
for needle in ('_make_tui_argv', 'Chat unavailable', 'ui-tui', 'tui_dist', 'embedded terminal requires'):
    idx = 0
    n = 0
    while n < 3:
        i = ws.find(needle, idx)
        if i < 0: break
        print(f'\n--- web_server {needle} @{i} ---')
        print(ws[max(0,i-200):i+500])
        idx = i+1
        n += 1
PY
