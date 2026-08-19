#!/usr/bin/env bash
set -euo pipefail
# Kill any stuck auth, then probe how openai-codex oauth works
pkill -f 'hermes auth add openai-codex' 2>/dev/null || true
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
# Find oauth implementation for openai-codex
python3 - <<PY
from pathlib import Path
site = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")
for p in site.rglob("*.py"):
    try:
        t = p.read_text(errors="ignore")
    except Exception:
        continue
    if "openai-codex" in t and ("device" in t.lower() or "oauth" in t.lower() or "auth.openai" in t):
        print("FILE", p)
PY
echo "=== auth add help ==="
hermes auth add --help 2>&1 | sed -n "1,80p"
' 
