#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
python3 - <<PY
from pathlib import Path
root=Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")
keys=("ascii","banner","welcome","HERMES","motd","splash","intro_art")
for p in root.rglob("*"):
  if p.suffix.lower() not in {".py",".tsx",".ts",".js",".md",".txt",".html"}: continue
  if "node_modules" in str(p) or "/pip/" in str(p): continue
  try: t=p.read_text(errors="ignore")
  except: continue
  low=t.lower()
  if "ascii" in low and ("hermes" in low or "banner" in low or "art" in low):
    if any(x in low for x in ("banner","splash","welcome","___","█","░")):
      print("CAND", p)
for p in [
 Path("/paperclip/.hermes/SOUL.md"),
 Path("/paperclip/.hermes/config.yaml"),
 Path("/paperclip/.hermes/IDENTITY.md"),
 Path("/paperclip/.hermes/BOOT.md"),
]:
  print("EXISTS", p, p.exists())
  if p.exists():
    print(p.read_text()[:500])
    print("---")
PY
# find ascii art files
find /paperclip/.hermes-venv -iname "*banner*" 2>/dev/null | head
grep -RIn "ascii_art\|banner_text\|welcome_banner\|display_name\|agent_name" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli /paperclip/.hermes-venv/lib/python3.13/site-packages/agent 2>/dev/null | head -40
'
