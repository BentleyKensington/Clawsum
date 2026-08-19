#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
import re
t=Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py').read_text()
for name in ['_is_accepted_host','_LOOPBACK_HOSTS','def create_app','bound_host','extra_hosts','accepted_hosts']:
    print('count', name, t.count(name))
# extract _is_accepted_host function
m=re.search(r'def _is_accepted_host\(.*?\n(?:.*?\n)*?    return .*\n', t)
# better: find line number
lines=t.splitlines()
start=None
for i,l in enumerate(lines):
    if l.startswith('def _is_accepted_host'):
        start=i
        break
if start is not None:
    for l in lines[start:start+80]:
        print(l)
        if l.startswith('def ') and 'accepted_host' not in l and lines.index(l)!=start:
            break
print('====')
# also check main.py dashboard launch for env
mt=Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli').joinpath('main.py')
# search config for dashboard allowed
for p in Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli').rglob('*.py'):
    s=p.read_text(errors='ignore')
    if 'allowed_host' in s.lower() or 'extra_origin' in s.lower() or 'DASHBOARD_ALLOWED' in s:
        print('HIT', p)
        for i,l in enumerate(s.splitlines(),1):
            if 'allowed_host' in l.lower() or 'DASHBOARD_ALLOWED' in l or 'trusted_origin' in l.lower():
                print(f'  {i}:{l[:140]}')
PY
