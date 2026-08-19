#!/usr/bin/env bash
set -euo pipefail
# Broader search for Clawsum OpenRouter keys OUTSIDE what we just wrote
python3 <<'PY'
from pathlib import Path
import hashlib
cur = None
p = Path("/docker/clawsum/secrets/openrouter.json")
if p.exists():
    import json
    cur = json.loads(p.read_text()).get("OPENROUTER_API_KEY","")
    print("current_secrets_fingerprint", hashlib.sha256(cur.encode()).hexdigest()[:12], "len", len(cur))

# search common secret locations for OTHER openrouter keys
needles = []
for root in [Path("/docker/clawsum"), Path("/root"), Path("/opt"), Path("/etc")]:
    if not root.exists(): continue
    for f in root.rglob("*"):
        if not f.is_file() or f.stat().st_size > 2_000_000: continue
        name = f.name.lower()
        if f.suffix not in {".env",".json",".yml",".yaml",".txt",".secret"} and "secret" not in str(f).lower() and "openrouter" not in name:
            continue
        try:
            t = f.read_text(errors="ignore")
        except Exception:
            continue
        if "sk-or-v1-" not in t and "OPENROUTER_API_KEY" not in t:
            continue
        # extract keys
        import re, json
        keys=set()
        for m in re.finditer(r"sk-or-v1-[A-Za-z0-9]+", t):
            keys.add(m.group(0))
        if f.suffix==".json":
            try:
                d=json.loads(t)
                def walk(o):
                    if isinstance(o, dict):
                        for k,v in o.items():
                            if isinstance(v,str) and v.startswith("sk-or-v1-"):
                                keys.add(v)
                            else:
                                walk(v)
                    elif isinstance(o, list):
                        for i in o: walk(i)
                walk(d)
            except Exception:
                pass
        for k in keys:
            fp = hashlib.sha256(k.encode()).hexdigest()[:12]
            same = (k == cur)
            needles.append((str(f), fp, len(k), same))

print("found_key_locations", len(needles))
for path, fp, ln, same in sorted(set(needles)):
    print(f"{'[SAME]' if same else '[OTHER]'} {fp} len={ln} @ {path}")
PY
