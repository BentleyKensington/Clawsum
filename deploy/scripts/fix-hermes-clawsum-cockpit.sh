#!/usr/bin/env bash
# Enable Clawsum cockpit plugin + point theme logos at public clawsum.com assets.
set -euo pipefail

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${ROOT}/examples/hermes-cockpit"

# Update config inside container (has PyYAML via hermes)
docker exec -u root "${CONTAINER}" bash -lc '
set -euo pipefail
export PATH="/paperclip/.hermes-venv/bin:$PATH"
python3 - <<PY
from pathlib import Path
try:
    import yaml
except ImportError:
    import json, re
    yaml = None

cfg_path = Path("/paperclip/.hermes/config.yaml")
raw = cfg_path.read_text() if cfg_path.exists() else ""
if yaml:
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        data = {}
else:
    data = {}
if not isinstance(data, dict):
    data = {}

dash = data.setdefault("dashboard", {})
if not isinstance(dash, dict):
    dash = {}
    data["dashboard"] = dash
dash["theme"] = "clawsum-command"

plugins = data.setdefault("plugins", {})
if not isinstance(plugins, dict):
    plugins = {}
    data["plugins"] = plugins
enabled = plugins.get("enabled")
if not isinstance(enabled, list):
    enabled = []
    plugins["enabled"] = enabled
if "clawsum-cockpit" not in enabled:
    enabled.append("clawsum-cockpit")
disabled = plugins.get("disabled")
if isinstance(disabled, list) and "clawsum-cockpit" in disabled:
    disabled.remove("clawsum-cockpit")

if yaml:
    cfg_path.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
else:
    # minimal fallback
    cfg_path.write_text(
        "dashboard:\n  theme: clawsum-command\nplugins:\n  enabled:\n    - clawsum-cockpit\n"
    )
print(cfg_path.read_text())
PY
hermes plugins enable clawsum-cockpit 2>&1 || true
hermes plugins list 2>&1 | head -50 || true
'

# Theme with public logos
install -m 644 "${SRC}/theme/clawsum-command.yaml" \
  /docker/clawsum/paperclip-data/.hermes/dashboard-themes/clawsum-command.yaml
docker cp "${SRC}/theme/clawsum-command.yaml" \
  "${CONTAINER}:/paperclip/.hermes/dashboard-themes/clawsum-command.yaml"

# Ensure plugin files present
docker exec -u root "${CONTAINER}" rm -rf /paperclip/.hermes/plugins/clawsum-cockpit
docker cp "${SRC}/plugin/clawsum-cockpit" \
  "${CONTAINER}:/paperclip/.hermes/plugins/clawsum-cockpit"
docker exec -u root "${CONTAINER}" mkdir -p \
  /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/assets
docker cp "${SRC}/assets/." \
  "${CONTAINER}:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/assets/"

# Hard restart dashboard
bash "${ROOT}/scripts/hermes-dashboard.sh" stop || true
docker exec -u root "${CONTAINER}" bash -lc 'pkill -9 -f "hermes dashboard" 2>/dev/null || true; rm -f /paperclip/logs/hermes-dashboard.pid'
sleep 1
bash "${ROOT}/scripts/hermes-dashboard.sh" start
sleep 3

echo "=== verify plugins ==="
curl -sS http://127.0.0.1:9119/api/dashboard/plugins | python3 -c 'import sys,json; d=json.load(sys.stdin); print([p["name"] for p in d])'
curl -sS http://127.0.0.1:9119/api/dashboard/themes | python3 -c 'import sys,json; d=json.load(sys.stdin); print("active=", d.get("active")); t=next((x for x in d["themes"] if x["name"]=="clawsum-command"),{}); print("assets=", (t.get("definition") or {}).get("assets"))'
echo DONE
