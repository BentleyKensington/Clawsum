#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
D=/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist
ls "$D" | head
python3 - <<PY
from pathlib import Path
import re
root = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist")
needles = ["assistant", "Assistant", "message-role", "data-role", "role\":\"assistant", "from-assistant", "isAssistant"]
hits = {}
for p in root.rglob("*.js"):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for n in needles:
        if n in t:
            hits.setdefault(n, []).append(str(p.name))
print("FILES", list(root.iterdir())[:20])
for n, fs in hits.items():
    print(n, "->", len(fs), fs[:3])
# extract nearby class-like strings
for p in root.rglob("*.js"):
    t = p.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r".{0,30}assistant.{0,50}", t, re.I):
        s = m.group(0).replace("\n"," ")[:120]
        if "class" in s.lower() or "role" in s.lower() or "message" in s.lower():
            print("CTX:", s)
            break
PY
'
