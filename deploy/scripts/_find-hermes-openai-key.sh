#!/usr/bin/env bash
set -euo pipefail
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
python3 - <<PY
from pathlib import Path
env = Path("/paperclip/.hermes/.env").read_text()
for line in env.splitlines():
    if "=" not in line: continue
    k,v = line.split("=",1)
    print(f"{k}=len={len(v)} prefix={v[:8]}...")
# Find how hermes detects openai key
import hermes_cli
import pkgutil, importlib
root = Path(hermes_cli.__file__).resolve().parent
print("hermes_cli", root)
PY
python3 - <<PY
from pathlib import Path
import re
site = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")
# Search for OpenAI STT/TTS label and OPENAI_API_KEY handling
hits = []
for p in site.rglob("*.py"):
    try:
        t = p.read_text(errors="ignore")
    except Exception:
        continue
    if "STT/TTS" in t or ("OPENAI_API_KEY" in t and "Anthropic" in t and "config" in p.name.lower()):
        hits.append(str(p))
    elif "OpenAI (STT" in t:
        hits.append(str(p))
print("files", len(hits))
for h in hits[:20]:
    print(h)
# Grep key snippets
for p in hits[:8]:
    text = Path(p).read_text(errors="ignore")
    for i,line in enumerate(text.splitlines()):
        if "OPENAI" in line or "STT" in line or "openai" in line.lower() and "key" in line.lower():
            if i < 4000:
                print(f"{p}:{i+1}:{line[:160]}")
PY
'
