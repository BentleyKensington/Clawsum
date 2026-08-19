#!/usr/bin/env bash
set -euo pipefail
curl -sS http://127.0.0.1:9119/assets/index-WrAtZQWO.js -o /tmp/hermes-dash.js
wc -c /tmp/hermes-dash.js
python3 <<'PY'
import re
t=open('/tmp/hermes-dash.js','r',errors='ignore').read()
# className template fragments with h-dvh / overflow
for needle in ['h-dvh', 'h-full overflow', 'overflow-y-auto', 'lg:overflow-hidden', 'min-h-0', 'flex-1 overflow']:
    idxs=[]
    start=0
    while len(idxs)<6:
        i=t.find(needle, start)
        if i<0: break
        idxs.append(i)
        start=i+len(needle)
    print('===', needle, 'hits', t.count(needle))
    for i in idxs:
        print(repr(t[max(0,i-60):i+100]))
PY
