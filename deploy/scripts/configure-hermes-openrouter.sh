#!/usr/bin/env bash
# Configure Clawsum Hermes dashboard LLM routing (adapted from CEOroof).
#
# Priority:
#   1. GPT via ChatGPT Plus / Codex OAuth (openai-codex) when Hermes has auth
#   2. OpenRouter free S1 for daily chat; escalation on 429
#
# Until Codex is connected (https://connect.clawsum.com or hermes auth add openai-codex),
# primary stays OpenRouter free → Anthropic escalation.
set -euo pipefail

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
HERMES_HOME="${HERMES_HOME_IN_CONTAINER:-/paperclip/.hermes}"
ENV_HOST="${CLAWSUM_ENV:-/docker/clawsum/.env}"
SECRET_HOST="${OPENROUTER_SECRET:-/docker/clawsum/secrets/openrouter.json}"
CODEX_MODEL="${HERMES_CODEX_MODEL:-gpt-5.4}"
OR_FREE_DEFAULT="${HERMES_OPENROUTER_MODEL:-nvidia/nemotron-3-super-120b-a12b:free}"
OR_CHEAP_MID_DEFAULT="${HERMES_OPENROUTER_CHEAP_MID:-google/gemini-2.5-flash}"
OR_ESCALATION_DEFAULT="${HERMES_OPENROUTER_ESCALATION:-anthropic/claude-sonnet-4.6}"
OR_FRONTIER_DEFAULT="${HERMES_OPENROUTER_FRONTIER:-google/gemini-2.5-pro}"
CONNECT_URL="${CLAWSUM_CONNECT_URL:-https://connect.clawsum.com}"

# Resolve OpenRouter key (prefer secrets file, else .env)
KEY="$(python3 - <<PY
import json
from pathlib import Path
sec = Path("${SECRET_HOST}")
env = Path("${ENV_HOST}")
key = ""
if sec.exists():
    data = json.loads(sec.read_text())
    key = (data.get("OPENROUTER_API_KEY") or data.get("api_key") or "").strip()
if not key and env.exists():
    for line in env.read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
if not key:
    raise SystemExit("OPENROUTER_API_KEY not found in ${SECRET_HOST} or ${ENV_HOST}")
print(key)
PY
)"

read -r OR_FREE OR_CHEAP_MID OR_ESCALATION OR_FRONTIER <<<"$(python3 - <<PY
from pathlib import Path
env = Path("${ENV_HOST}")
vals = {}
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            vals[k.strip()] = v.strip().strip('"').strip("'")
free_m = vals.get("OPENROUTER_FREE_MODEL") or vals.get("OPENROUTER_S1_MODEL") or "${OR_FREE_DEFAULT}"
cheap_m = vals.get("OPENROUTER_CHEAP_MID_MODEL") or "${OR_CHEAP_MID_DEFAULT}"
esc_m = vals.get("OPENROUTER_ESCALATION_MODEL") or "${OR_ESCALATION_DEFAULT}"
front_m = vals.get("OPENROUTER_FRONTIER_MODEL") or "${OR_FRONTIER_DEFAULT}"
print(free_m, cheap_m, esc_m, front_m)
PY
)"

HAS_CODEX="$(docker exec -u root -e HERMES_HOME="$HERMES_HOME" -e PATH=/paperclip/.hermes-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "$CONTAINER" \
  hermes auth list 2>/dev/null | grep -qi 'openai-codex' && echo 1 || echo 0)"

if [[ "$HAS_CODEX" == "1" ]]; then
  PRIMARY_PROVIDER="openai-codex"
  PRIMARY_MODEL="$CODEX_MODEL"
  echo "Configuring Hermes: GPT/Codex primary (${PRIMARY_MODEL})"
  echo "  Fallback chain: ${OR_FREE} → ${OR_CHEAP_MID} → ${OR_ESCALATION} → ${OR_FRONTIER}"
else
  PRIMARY_PROVIDER="openrouter"
  PRIMARY_MODEL="$OR_FREE"
  echo "Configuring Hermes: OpenRouter interim primary (${PRIMARY_MODEL}) — GPT/Codex not connected yet"
  echo "  Fallback chain: ${OR_CHEAP_MID} → ${OR_ESCALATION} → ${OR_FRONTIER}"
  echo "  Connect GPT: ${CONNECT_URL}  (then re-run this script)"
fi

docker exec -i -u root \
  -e OR_KEY="$KEY" \
  -e PRIMARY_PROVIDER="$PRIMARY_PROVIDER" \
  -e PRIMARY_MODEL="$PRIMARY_MODEL" \
  -e OR_FREE="$OR_FREE" \
  -e OR_CHEAP_MID="$OR_CHEAP_MID" \
  -e OR_ESCALATION="$OR_ESCALATION" \
  -e OR_FRONTIER="$OR_FRONTIER" \
  -e HAS_CODEX="$HAS_CODEX" \
  -e PATH=/paperclip/.hermes-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  -e HOME=/paperclip \
  -e HERMES_HOME="$HERMES_HOME" \
  "$CONTAINER" python3 - <<'PY'
import os
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

home = Path("/paperclip/.hermes")
home.mkdir(parents=True, exist_ok=True)
env_path = home / ".env"
cfg_path = home / "config.yaml"

key = os.environ["OR_KEY"]
primary_provider = os.environ["PRIMARY_PROVIDER"]
primary_model = os.environ["PRIMARY_MODEL"]
or_free = os.environ["OR_FREE"]
or_cheap = os.environ.get("OR_CHEAP_MID", "google/gemini-2.5-flash")
or_esc = os.environ["OR_ESCALATION"]
or_front = os.environ.get("OR_FRONTIER", "google/gemini-2.5-pro")
has_codex = os.environ.get("HAS_CODEX") == "1"

lines = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        lines[k.strip()] = v

lines["OPENROUTER_API_KEY"] = key
lines.setdefault("OPENROUTER_HTTP_REFERER", "https://clawsum.com")
lines.setdefault("OPENROUTER_APP_TITLE", "Clawsum Hermes")

out = "\n".join(f"{k}={v}" for k, v in lines.items()) + "\n"
env_path.write_text(out)
env_path.chmod(0o600)
print("wrote", env_path, "keys", sorted(k for k in lines if "KEY" not in k and "TOKEN" not in k))

# Preserve plugins/dashboard/display when possible; always rewrite model blocks cleanly.
raw = cfg_path.read_text() if cfg_path.exists() else ""
plugins = ["clawsum-cockpit", "clawsum-inbox", "clawsum-agents", "clawsum-skills"]
theme = "clawsum-command"
skin = "clawsum"
data = None
if yaml is not None:
    try:
        data = yaml.safe_load(raw) if raw.strip() else {}
    except Exception:
        data = None
if isinstance(data, dict):
    pl = data.get("plugins") if isinstance(data.get("plugins"), dict) else {}
    en = pl.get("enabled") if isinstance(pl, dict) else None
    if isinstance(en, list) and en:
        plugins = [str(x) for x in en]
    dash = data.get("dashboard") if isinstance(data.get("dashboard"), dict) else {}
    theme = dash.get("theme") or theme
    disp = data.get("display") if isinstance(data.get("display"), dict) else {}
    skin = disp.get("skin") or skin
else:
    m = re.search(r"enabled:\s*\n((?:\s*-\s*[^\n]+\n)+)", raw)
    if m:
        found = re.findall(r"-\s*([^\n]+)", m.group(1))
        if found:
            plugins = [x.strip() for x in found]

if has_codex:
    model = {"provider": primary_provider, "default": primary_model}
    fallbacks = [
        {"provider": "openrouter", "model": or_free},
        {"provider": "openrouter", "model": or_cheap},
        {"provider": "openrouter", "model": or_esc},
        {"provider": "openrouter", "model": or_front},
    ]
else:
    model = {"provider": primary_provider, "default": primary_model}
    fallbacks = [
        {"provider": "openrouter", "model": or_cheap},
        {"provider": "openrouter", "model": or_esc},
        {"provider": "openrouter", "model": or_front},
    ]

ordered = {
    "model": model,
    "fallback_providers": fallbacks,
    "dashboard": {"theme": theme},
    "plugins": {"enabled": plugins},
    "display": {"skin": skin},
}
if yaml is not None:
    cfg_path.write_text(yaml.safe_dump(ordered, sort_keys=False, default_flow_style=False))
else:
    text = (
        "model:\n"
        f"  provider: {model['provider']}\n"
        f"  default: {model['default']}\n"
        "fallback_providers:\n"
    )
    for fb in fallbacks:
        text += f"  - provider: {fb['provider']}\n    model: {fb['model']}\n"
    text += f"dashboard:\n  theme: {theme}\nplugins:\n  enabled:\n"
    for p in plugins:
        text += f"  - {p}\n"
    text += f"display:\n  skin: {skin}\n"
    cfg_path.write_text(text)

print("wrote", cfg_path)
print(cfg_path.read_text())
PY

docker exec -u root -e HERMES_HOME="$HERMES_HOME" -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin "$CONTAINER" \
  hermes auth reset openrouter 2>/dev/null || true

echo "=== hermes model / fallback ==="
docker exec -u root -e HERMES_HOME="$HERMES_HOME" -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin "$CONTAINER" \
  hermes config show 2>&1 | sed -n '/Model/,/Display/p'
docker exec -u root -e HERMES_HOME="$HERMES_HOME" -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin "$CONTAINER" \
  hermes fallback list 2>&1 | sed -n '1,40p'

# Restart dashboard so routing takes effect
if [[ -x /docker/clawsum/scripts/hermes-dashboard.sh ]]; then
  bash /docker/clawsum/scripts/hermes-dashboard.sh stop || true
  sleep 1
  bash /docker/clawsum/scripts/hermes-dashboard.sh start
fi

echo "Done. Hard-refresh boss chat (or New chat)."
echo "GPT primary requires Connect → Codex OAuth, then re-run this script."
