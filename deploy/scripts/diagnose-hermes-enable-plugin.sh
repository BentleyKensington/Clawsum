#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
python3 <<PY
from pathlib import Path
# Find _get_dashboard_plugins and enable logic
for rel in [
 "hermes_cli/web_server.py",
 "hermes_cli/plugins.py",
 "hermes_cli/config.py",
]:
 p=Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")/rel
 t=p.read_text()
 for needle in ["_get_dashboard_plugins","def discover_dashboard","plugins.enabled","enabled_plugins","allow_user_dashboard","source == \"user\"","dashboard plugin"]:
  idx=0
  while True:
   i=t.find(needle, idx)
   if i<0: break
   print(f"\n===== {rel} @ {needle} =====")
   print(t[max(0,i-300):i+900])
   idx=i+len(needle)
   if idx>len(t): break
PY
# show current plugins config
echo "=== config plugins section ==="
python3 - <<PY
from pathlib import Path
import yaml
cfg=Path("/paperclip/.hermes/config.yaml")
print(cfg.read_text())
# also check if there is plugins.yaml
for p in Path("/paperclip/.hermes").glob("*plugin*"):
 print("FILE", p)
PY
ls /paperclip/.hermes-venv/bin/hermes
/paperclip/.hermes-venv/bin/hermes plugins --help 2>&1 | head -40
'
