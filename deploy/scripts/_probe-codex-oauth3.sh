#!/usr/bin/env bash
set -euo pipefail
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
python3 - <<PY
from pathlib import Path
for rel in [
 "hermes_cli/auth.py",
 "hermes_cli/auth_commands.py",
 "plugins/model-providers/openai-codex/__init__.py",
 "hermes_cli/subcommands/auth.py",
]:
 p = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")/rel
 print("====", rel, "====")
 t = p.read_text(errors="ignore")
 # print relevant chunks
 keys = ("device", "manual_paste", "no_browser", "auth.openai", "codex", "callback", "user_code", "verification")
 lines = t.splitlines()
 for i, line in enumerate(lines):
  low = line.lower()
  if any(k in low for k in keys) or "oauth" in low and ("url" in low or "print" in low or "open(" in low):
   start=max(0,i-1); end=min(len(lines), i+2)
   for j in range(start,end):
    print(f"{j+1}:{lines[j][:160]}")
   print("---")
PY
'
