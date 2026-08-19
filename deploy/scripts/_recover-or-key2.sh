#!/usr/bin/env bash
set -euo pipefail
echo "=== .env mtime / nearby backups ==="
ls -la --time-style=long-iso /docker/clawsum/.env /docker/clawsum/.env* 2>/dev/null || true
lsattr /docker/clawsum/.env 2>/dev/null || true
# editor/swap leftovers
find /docker/clawsum -maxdepth 2 \( -name '.env*' -o -name '*env*~' -o -name '*.env.swp' \) 2>/dev/null
echo "=== openclaw auth / models for openrouter ==="
find /docker/clawsum/data -iname '*openrouter*' -o -iname '*auth*' 2>/dev/null | sed -n '1,60p'
python3 <<'PY'
from pathlib import Path
import json, hashlib, re
roots=[
 Path('/docker/clawsum/data'),
 Path('/docker/clawsum/paperclip-data'),
 Path('/docker/openclaw-qpr7'),
]
pat=re.compile(r'sk-or-v1-[A-Za-z0-9_-]{20,}')
for root in roots:
  if not root.exists():
    print('missing', root); continue
  print('scanning', root)
  for f in root.rglob('*'):
    if not f.is_file() or f.stat().st_size>3_000_000: continue
    try:
      t=f.read_text(errors='ignore')
    except Exception:
      continue
    if 'openrouter' not in t.lower() and 'sk-or-v1-' not in t:
      continue
    keys=pat.findall(t)
    # also provider blocks
    has_or = 'openrouter' in t.lower()
    if keys or has_or:
      print('FILE', f, 'keys', len(set(keys)), 'mentions_openrouter', has_or)
      for k in sorted(set(keys)):
        print('  fp', hashlib.sha256(k.encode()).hexdigest()[:12], 'len', len(k))
PY

echo "=== openclaw.json model providers (no secrets) ==="
python3 <<'PY'
from pathlib import Path
import json
for p in [
 Path('/docker/clawsum/data/.openclaw/openclaw.json'),
 Path('/docker/clawsum/data/.openclaw/openclaw.json.bak'),
]:
  print('---', p, p.exists())
  if not p.exists(): continue
  try:
    d=json.loads(p.read_text())
  except Exception as e:
    print('parse', e); continue
  # walk for provider/model/auth keys names only
  def walk(o, path=''):
    if isinstance(o, dict):
      for k,v in o.items():
        pk=f'{path}.{k}' if path else k
        kl=k.lower()
        if any(x in kl for x in ('openrouter','provider','model','auth','apiKey','api_key')):
          if isinstance(v, str):
            if v.startswith('sk-') or 'key' in kl:
              print(pk, '= ***len', len(v))
            else:
              print(pk, '=', v[:120])
          elif isinstance(v, (int,float,bool)) or v is None:
            print(pk, '=', v)
          else:
            print(pk, '=', type(v).__name__)
        walk(v, pk)
    elif isinstance(o, list) and len(o)<30:
      for i,v in enumerate(o):
        walk(v, f'{path}[{i}]')
  walk(d)
PY

echo "=== compose env_file / grep OPENROUTER in yaml ==="
grep -RIn --include='*.yml' --include='*.yaml' -E 'OPENROUTER|openrouter' /docker/clawsum --exclude-dir=paperclip-data --exclude-dir=.hermes-venv 2>/dev/null | sed -n '1,40p' || true

echo "=== filesystem snapshots? ==="
which snapper btrfs restic borg 2>/dev/null || true
ls /.snapshots 2>/dev/null | sed -n '1,10p' || true
ls /docker/clawsum/.zfs 2>/dev/null || true

echo "=== shell history mentions ==="
grep -n 'OPENROUTER\|sk-or-v1\|openrouter.json' /root/.bash_history 2>/dev/null | sed -n '1,30p' || true
grep -n 'OPENROUTER\|sk-or-v1\|openrouter.json' /root/.zsh_history 2>/dev/null | sed -n '1,30p' || true
