#!/usr/bin/env bash
set -euo pipefail
# Fix Hermes config model/fallback cleanly; check OpenClaw codex auth; restart dashboard.

echo "=== OpenClaw auth-profiles: openai-codex? ==="
python3 <<'PY'
from pathlib import Path
import json
hits = 0
for f in Path("/docker/clawsum/data/.openclaw").rglob("auth-profiles.json"):
    try:
        d = json.loads(f.read_text())
    except Exception:
        continue
    text = json.dumps(d)
    if "openai-codex" in text or "codex" in text.lower():
        # summarize providers/types only
        def walk(o, path=""):
            if isinstance(o, dict):
                prov = o.get("provider") or o.get("type") or o.get("mode")
                if prov and ("codex" in str(prov).lower() or "openai" in str(prov).lower()):
                    print(f.name if False else str(f), path or ".", "provider/type=", prov)
                for k,v in o.items():
                    walk(v, f"{path}.{k}" if path else k)
            elif isinstance(o, list):
                for i,v in enumerate(o[:50]):
                    walk(v, f"{path}[{i}]")
        print("FILE", f)
        walk(d)
        hits += 1
print("auth-profiles_with_codex_mentions", hits)
# also openclaw.json models
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
if p.exists():
    d = json.loads(p.read_text())
    def walk(o, path=""):
        if isinstance(o, dict):
            for k,v in o.items():
                pk = f"{path}.{k}" if path else k
                if any(x in pk.lower() for x in ("model", "provider", "auth", "primary", "fallback")):
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        s = str(v)
                        if s.startswith("sk-") or "token" in pk.lower() or "key" in pk.lower():
                            print(pk, "=***")
                        else:
                            print(pk, "=", s[:120])
                walk(v, pk)
        elif isinstance(o, list) and "model" in path.lower():
            for i,v in enumerate(o[:20]):
                walk(v, f"{path}[{i}]")
    print("--- openclaw.json model/provider ---")
    walk(d)
PY

echo "=== rewrite Hermes model/fallback cleanly ==="
docker exec -i -u root clawsum-paperclip-1 python3 <<'PY'
from pathlib import Path
import re, yaml

cfg = Path("/paperclip/.hermes/config.yaml")
text = cfg.read_text() if cfg.exists() else ""
# parse as yaml if possible, else strip blocks
try:
    data = yaml.safe_load(text) or {}
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}

# detect codex
import subprocess
auth = subprocess.check_output(
    ["hermes", "auth", "list"],
    env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "HERMES_HOME": "/paperclip/.hermes", "PATH": "/paperclip/.hermes-venv/bin:/usr/bin:/bin", "HOME": "/paperclip"},
    text=True,
    stderr=subprocess.STDOUT,
)
has_codex = "openai-codex" in auth.lower()
print("has_codex", has_codex)
print(auth)

# read models from hermes .env / host not available; use known defaults
or_free = "nvidia/nemotron-3-super-120b-a12b:free"
or_esc = "anthropic/claude-sonnet-4.6"

# drop stale keys
for k in ("model", "fallback_model", "fallback_providers", "provider"):
    data.pop(k, None)

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

# keep dashboard/plugins/display
dash = data.setdefault("dashboard", {})
if isinstance(dash, dict) and not dash.get("theme"):
    dash["theme"] = "clawsum-command"
disp = data.setdefault("display", {})
if isinstance(disp, dict) and not disp.get("skin"):
    disp["skin"] = "clawsum"

# write with stable key order-ish: model first
ordered = {}
for k in ("model", "fallback_providers", "dashboard", "plugins", "display"):
    if k in data:
        ordered[k] = data.pop(k)
ordered.update(data)
cfg.write_text(yaml.safe_dump(ordered, sort_keys=False, default_flow_style=False))
print("--- wrote ---")
print(cfg.read_text())
PY

docker exec -u root -e HERMES_HOME=/paperclip/.hermes -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin \
  clawsum-paperclip-1 hermes auth reset openrouter 2>/dev/null || true

echo "=== restart dashboard ==="
bash /docker/clawsum/scripts/hermes-dashboard.sh stop || true
sleep 1
bash /docker/clawsum/scripts/hermes-dashboard.sh start
sleep 2
curl -sS -o /dev/null -w "hermes=%{http_code}\n" http://127.0.0.1:9119/ || true

echo "=== verify ==="
docker exec -u root -e HERMES_HOME=/paperclip/.hermes -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin \
  clawsum-paperclip-1 hermes auth list 2>&1 | sed -n '1,40p'
docker exec -u root -e HERMES_HOME=/paperclip/.hermes -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin \
  clawsum-paperclip-1 hermes fallback list 2>&1 | sed -n '1,40p'
docker exec -u root clawsum-paperclip-1 python3 -c 'from pathlib import Path; print(Path("/paperclip/.hermes/config.yaml").read_text())'
echo DONE
