#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
python3 <<PY
from pathlib import Path
import re
root=Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli")
for p in sorted(root.rglob("*.py")):
  t=p.read_text(errors="ignore")
  if "dashboard" in t and "plugin" in t and ("bundled" in t or "discover" in t or "plugins/" in t):
    hits=[]
    for i,l in enumerate(t.splitlines(),1):
      if any(k in l for k in ("bundled","discover_dashboard","list_dashboard","user plugin","plugins_dir","dashboard_plugins","source")):
        hits.append(f"{i}:{l.strip()[:140]}")
    if hits:
      print("FILE", p)
      print("\n".join(hits[:40]))
      print("---")
PY
'
