#!/usr/bin/env bash
set -euo pipefail
# Focus on OpenClaw auth profiles / gateway secrets
python3 <<'PY'
from pathlib import Path
import json, hashlib, re
pat=re.compile(r'sk-or-v1-[A-Za-z0-9_-]{20,}')
candidates=[]
for root in [Path('/docker/clawsum/data'), Path('/docker/openclaw-qpr7')]:
  if not root.exists():
    continue
  for f in root.rglob('*'):
    if not f.is_file() or f.stat().st_size>5_000_000: continue
    name=f.name.lower()
    if not any(x in name or x in str(f).lower() for x in ['auth','secret','openclaw','credential','provider','api']):
      if f.suffix not in {'.json','.yaml','.yml','.env'}:
        continue
    try:
      raw=f.read_bytes()
    except Exception:
      continue
    if b'sk-or-v1-' not in raw and b'openrouter' not in raw.lower() and b'OPENROUTER' not in raw:
      continue
    t=raw.decode('utf-8','ignore')
    keys=sorted(set(pat.findall(t)))
    print('HIT', f, 'or_keys', len(keys), 'size', f.stat().st_size)
    for k in keys:
      print('  fp', hashlib.sha256(k.encode()).hexdigest()[:12])
    # if json, show openrouter-related key paths without values
    if f.suffix=='.json':
      try:
        d=json.loads(t)
      except Exception:
        continue
      def walk(o,p=''):
        if isinstance(o,dict):
          for kk,vv in o.items():
            pk=f'{p}.{kk}' if p else kk
            if 'openrouter' in pk.lower() or (isinstance(vv,str) and ('openrouter' in vv.lower() or vv.startswith('sk-or'))):
              if isinstance(vv,str) and vv.startswith('sk-'):
                print('  path', pk, '***', hashlib.sha256(vv.encode()).hexdigest()[:12])
              elif isinstance(vv,str):
                print('  path', pk, '=', vv[:80])
              else:
                print('  path', pk, type(vv).__name__)
            walk(vv,pk)
        elif isinstance(o,list):
          for i,vv in enumerate(o[:50]):
            walk(vv,f'{p}[{i}]')
      walk(d)
PY

echo "=== compare CEOroof vs Clawsum fingerprint ==="
python3 <<'PY'
import hashlib, json
from pathlib import Path
# only clawsum local; ceoroof remote not available here unless we ssh - skip
p=Path('/docker/clawsum/secrets/openrouter.json')
k=json.loads(p.read_text())['OPENROUTER_API_KEY']
print('clawsum_now', hashlib.sha256(k.encode()).hexdigest()[:12], 'len', len(k), 'prefix', k[:11])
PY

# extundelete / debugfs unlikely; check journald for old .env cat? no
# look for configure-openrouter-escalation state files
find /docker/clawsum -name '*escalat*' -o -name '*llm_policy*' -o -name '*openrouter*' 2>/dev/null | sed -n '1,40p'
