#!/usr/bin/env bash
set -euo pipefail
# Does Hermes accept anthropic as fallback_provider without OpenRouter?
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
hermes fallback --help 2>&1 | sed -n "1,60p"
hermes fallback list 2>&1 | sed -n "1,40p"
python3 - <<PY
from pathlib import Path
site=Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")
for p in site.rglob("*.py"):
    try: t=p.read_text(errors="ignore")
    except Exception: continue
    if "fallback_providers" in t and "openrouter" in t:
        print(p)
        break
PY
'
