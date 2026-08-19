#!/usr/bin/env bash
set -euo pipefail
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
python3 - <<PY
from pathlib import Path
import subprocess, os, yaml
auth = subprocess.check_output(["hermes","auth","list"], text=True, stderr=subprocess.STDOUT)
has_codex = "openai-codex" in auth.lower()
print("has_codex", has_codex)
cfg = Path("/paperclip/.hermes/config.yaml")
data = yaml.safe_load(cfg.read_text()) if cfg.exists() else {}
if not isinstance(data, dict):
    data = {}
for k in ("model", "fallback_model", "fallback_providers", "provider"):
    data.pop(k, None)
or_free = "nvidia/nemotron-3-super-120b-a12b:free"
or_esc = "anthropic/claude-sonnet-4.6"
if has_codex:
    data["model"] = {"provider": "openai-codex", "default": "gpt-5.4"}
    data["fallback_providers"] = [
        {"provider": "openrouter", "model": or_free},
        {"provider": "openrouter", "model": or_esc},
    ]
else:
    data["model"] = {"provider": "openrouter", "default": or_free}
    data["fallback_providers"] = [
        {"provider": "openrouter", "model": or_esc},
    ]
dash = data.setdefault("dashboard", {})
if isinstance(dash, dict):
    dash.setdefault("theme", "clawsum-command")
disp = data.setdefault("display", {})
if isinstance(disp, dict):
    disp.setdefault("skin", "clawsum")
ordered = {}
for k in ("model", "fallback_providers", "dashboard", "plugins", "display"):
    if k in data:
        ordered[k] = data.pop(k)
ordered.update(data)
cfg.write_text(yaml.safe_dump(ordered, sort_keys=False, default_flow_style=False))
print(cfg.read_text())
PY
hermes auth reset openrouter 2>/dev/null || true
hermes fallback list 2>&1 | sed -n "1,40p"
hermes auth list 2>&1 | sed -n "1,40p"
'
bash /docker/clawsum/scripts/hermes-dashboard.sh stop || true
sleep 1
bash /docker/clawsum/scripts/hermes-dashboard.sh start
sleep 2
curl -sS -o /dev/null -w "hermes=%{http_code}\n" http://127.0.0.1:9119/ || true
echo DONE
