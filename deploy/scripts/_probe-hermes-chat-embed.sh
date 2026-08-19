#!/usr/bin/env bash
set +u
docker exec clawsum-paperclip-1 bash -lc '
rg -n "embed|layoutVariant|chat.dock|iframe|prefill|initialPrompt|draft=" \
  /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py \
  2>/dev/null | head -40
echo ---
# look for query handling in minified assets (small needles)
python3 - <<PY
from pathlib import Path
p=Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets")
for f in p.glob("index-*.js"):
    t=f.read_text(errors="ignore")
    for needle in ["embed=","?prompt","prefill","initialMessage","compose=","newSession","session_start"]:
        if needle in t:
            i=t.find(needle)
            print(f.name, needle, t[max(0,i-60):i+80].replace("\n"," ")[:140])
PY
'
