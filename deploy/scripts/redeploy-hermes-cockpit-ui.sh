#!/usr/bin/env bash
set -euo pipefail
CONTAINER=clawsum-paperclip-1
SRC=/docker/clawsum/examples/hermes-cockpit

# Ensure plugin files (incl authority.json) in Hermes home
docker exec -u root "$CONTAINER" rm -rf /paperclip/.hermes/plugins/clawsum-cockpit
docker cp "$SRC/plugin/clawsum-cockpit" "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit"
docker exec -u root "$CONTAINER" mkdir -p /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/assets
docker cp "$SRC/assets/." "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/assets/" 2>/dev/null || true
docker cp "$SRC/theme/clawsum-command.yaml" "$CONTAINER:/paperclip/.hermes/dashboard-themes/clawsum-command.yaml" 2>/dev/null || true

# Enable plugin + theme via hermes venv python (has PyYAML)
docker exec -u root "$CONTAINER" bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
python3 - <<PY
from pathlib import Path
import yaml
p = Path("/paperclip/.hermes/config.yaml")
try:
    data = yaml.safe_load(p.read_text()) if p.exists() else {}
except Exception:
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
p.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
print(p.read_text())
PY
'

bash /docker/clawsum/scripts/hermes-dashboard.sh stop || true
docker exec -u root "$CONTAINER" bash -lc 'pkill -9 -f "hermes dashboard" || true; rm -f /paperclip/logs/hermes-dashboard.pid'
sleep 1
bash /docker/clawsum/scripts/hermes-dashboard.sh start
sleep 3

echo "=== plugins ==="
curl -sS http://127.0.0.1:9119/api/dashboard/plugins | python3 -c "import sys,json; print([p['name'] for p in json.load(sys.stdin)])"

# Authority needs session token — check file present + try with SPA bootstrap
echo "=== authority file ==="
docker exec "$CONTAINER" ls -la /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/authority.json /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js

echo "=== probe authority via python in container (mount check) ==="
docker exec -u root "$CONTAINER" bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
python3 - <<PY
import json
from pathlib import Path
p=Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/authority.json")
d=json.loads(p.read_text())
print("agents", len(d.get("agents",[])), "skills", len(d.get("skills",[])))
# quick import of router load
import sys
sys.path.insert(0, "/paperclip/.hermes/plugins/clawsum-cockpit/dashboard")
# just confirm index.js mentions left nav
t=Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js").read_text()
for needle in ["Agents", "Skills", "inbox", "clawsum-nav", "/authority"]:
    print(needle, needle in t or needle.lower() in t.lower())
PY
'
echo DONE
