#!/usr/bin/env bash
set -euo pipefail
echo "=== Hermes model + keys ==="
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
python3 - <<PY
from pathlib import Path
import yaml, os
# load .env manually like hermes
envp=Path("/paperclip/.hermes/.env")
for line in envp.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k,v=line.split("=",1); os.environ.setdefault(k,v)
cfg=yaml.safe_load(Path("/paperclip/.hermes/config.yaml").read_text())
print("hermes_model", cfg.get("model"))
print("OPENAI_API_KEY", "yes" if os.environ.get("OPENAI_API_KEY") else "no", "len", len(os.environ.get("OPENAI_API_KEY") or ""))
print("VOICE_TOOLS_OPENAI_KEY", "yes" if os.environ.get("VOICE_TOOLS_OPENAI_KEY") else "no")
print("ANTHROPIC_API_KEY", "yes" if os.environ.get("ANTHROPIC_API_KEY") else "no")
PY
'
echo "=== OpenClaw openai presence (host env, masked) ==="
# Paperclip/OpenClaw container env — do not print secrets
docker exec clawsum-paperclip-1 bash -lc 'python3 - <<PY
import os
print("container_OPENAI", "yes" if os.environ.get("OPENAI_API_KEY") else "no")
print("container_ANTHROPIC", "yes" if os.environ.get("ANTHROPIC_API_KEY") else "no")
PY'
# Check openclaw config if present
if docker exec clawsum-paperclip-1 bash -lc 'test -f /paperclip/.openclaw/openclaw.json || test -f /home/node/.openclaw/openclaw.json'; then
  docker exec clawsum-paperclip-1 bash -lc '
  for f in /paperclip/.openclaw/openclaw.json /home/node/.openclaw/openclaw.json; do
    [ -f "$f" ] || continue
    echo "openclaw_cfg=$f"
    python3 - <<PY
import json
from pathlib import Path
p=Path("'"$f"'")
try:
  d=json.loads(p.read_text())
except Exception as e:
  print("parse_err", e); raise SystemExit
# print model/provider-ish keys only
def walk(obj, path=""):
  if isinstance(obj, dict):
    for k,v in obj.items():
      pk=f"{path}.{k}" if path else k
      kl=k.lower()
      if any(x in kl for x in ("model","provider","openai","anthropic","primary","default")):
        if isinstance(v,(str,int,float,bool)) or v is None:
          s=str(v)
          if "sk-" in s or "key" in kl:
            s="***"
          print(pk, "=", s[:120])
        elif isinstance(v, dict):
          print(pk, "= {…}")
          walk(v, pk)
        else:
          print(pk, "=", type(v).__name__)
      else:
        walk(v, pk)
  elif isinstance(obj, list) and path:
    pass
walk(d)
PY
  done
  '
fi
echo DONE
