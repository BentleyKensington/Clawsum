#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
find /paperclip/.hermes-venv /paperclip -path "*dashboard*" -name "*.js" 2>/dev/null | head -40
echo ---
# Running dashboard process cwd / files
ls -la /proc/$(pgrep -f "hermes dashboard" | head -1)/cwd 2>/dev/null || true
python3 - <<PY
import os,glob
for root in ["/paperclip/.hermes-venv/lib","/paperclip"]:
  for pat in ["**/dashboard/**/*.js","**/static/**/*.js","**/frontend/**/*.js"]:
    pass
# search site-packages for hermes
import pathlib
hits=[]
for p in pathlib.Path("/paperclip/.hermes-venv").rglob("*.js"):
  s=str(p)
  if "node_modules" in s: continue
  if p.stat().st_size>500000: continue
  try:
    t=p.read_text(errors="ignore")
  except Exception:
    continue
  if "Send" in t and ("composer" in t.lower() or "textarea" in t.lower()) and "speech" not in s.lower():
    hits.append(s)
    if len(hits)>=15: break
print("hits",len(hits))
for h in hits[:15]:
  print(h)
PY
'
