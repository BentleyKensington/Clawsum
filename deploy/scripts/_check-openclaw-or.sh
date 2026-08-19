#!/usr/bin/env bash
set -euo pipefail
python3 <<'PY'
from pathlib import Path
import json, hashlib
p = Path('/docker/clawsum/data/.openclaw/openclaw.json')
print('openclaw.json', p.exists(), 'size', p.stat().st_size if p.exists() else 0)
if p.exists():
    d = json.loads(p.read_text())
    def walk(o, path=''):
        if isinstance(o, dict):
            for k,v in o.items():
                pk = f'{path}.{k}' if path else k
                if 'openrouter' in pk.lower() or (isinstance(v,str) and ('openrouter' in v.lower() or v.startswith('sk-or'))):
                    if isinstance(v,str) and v.startswith('sk-'):
                        print(pk, 'fp', hashlib.sha256(v.encode()).hexdigest()[:12], 'len', len(v))
                    elif isinstance(v,str):
                        print(pk, '=', v[:100])
                    else:
                        print(pk, type(v).__name__)
                walk(v, pk)
        elif isinstance(o, list):
            for i,v in enumerate(o[:100]):
                walk(v, f'{path}[{i}]')
    walk(d)
# auth profiles dir
for root in [Path('/docker/clawsum/data/.openclaw'), Path('/docker/clawsum/data/.openclaw-auth-secrets')]:
    if not root.exists():
        print('missing', root); continue
    print('list', root)
    for f in sorted(root.rglob('*'))[:80]:
        if f.is_file() and f.stat().st_size < 500000:
            if 'openrouter' in f.name.lower() or 'auth' in f.name.lower() or f.suffix=='.json':
                try:
                    t=f.read_text(errors='ignore')
                except Exception:
                    continue
                if 'sk-or-v1-' in t or 'OPENROUTER' in t:
                    print(' KEYFILE', f)
PY
