#!/usr/bin/env bash
set -euo pipefail
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
echo "=== hermes auth help ==="
hermes auth --help 2>&1 | sed -n "1,80p" || true
echo "=== hermes auth add help ==="
hermes auth add --help 2>&1 | sed -n "1,80p" || true
echo "=== grep openai-codex in package ==="
python3 - <<PY
from pathlib import Path
site=Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")
hits=0
for p in site.rglob("*.py"):
    try: t=p.read_text(errors="ignore")
    except Exception: continue
    if "openai-codex" in t or "openai_codex" in t:
        hits+=1
        if hits<=12:
            print(p)
print("hit_files", hits)
PY
echo "=== hermes version ==="
hermes --version 2>&1 || true
'
# OpenClaw: look for codex / chatgpt oauth mentions in container
docker exec clawsum-paperclip-1 bash -lc '
python3 - <<PY
from pathlib import Path
cands=[]
for root in [Path("/paperclip"), Path("/home/node"), Path("/app")]:
  if not root.exists(): continue
  for p in root.rglob("*"):
    if p.is_file() and p.suffix in {".json",".md",".yml",".yaml"} and p.stat().st_size < 2_000_000:
      name=p.name.lower()
      if "openclaw" in str(p).lower() or name in {"openclaw.json","config.json"}:
        cands.append(p)
print("cfg_cands", len(cands))
for p in cands[:20]:
  print(p)
PY
which openclaw 2>/dev/null || true
ls /usr/local/bin 2>/dev/null | sed -n "1,40p" || true
' 2>/dev/null | sed -n "1,60p"
