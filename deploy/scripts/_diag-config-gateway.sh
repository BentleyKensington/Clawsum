#!/usr/bin/env bash
set +u
set -eo pipefail
echo "=== config.yaml ==="
docker exec clawsum-paperclip-1 head -80 /paperclip/.hermes/config.yaml
echo
echo "=== yaml parse ==="
docker exec clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; python3 - <<"PY"
from pathlib import Path
import yaml
p=Path("/paperclip/.hermes/config.yaml")
try:
    data=yaml.safe_load(p.read_text())
    print("OK", type(data), list(data.keys()) if isinstance(data, dict) else data)
    print("plugins", (data or {}).get("plugins"))
    print("dashboard", (data or {}).get("dashboard"))
    print("model", (data or {}).get("model"))
except Exception as e:
    print("FAIL", e)
PY'

echo "=== gateway status ==="
docker exec clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes gateway status 2>&1 | head -40; hermes status 2>&1 | head -50'

echo "=== index.js checks ==="
docker exec clawsum-paperclip-1 bash -lc 'node --check /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js; echo node_exit:$?'
docker exec clawsum-paperclip-1 bash -lc 'grep -c "Session Startup Briefs\|SidebarSlot\|PLUGINS.registerSlot" /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js'
docker exec clawsum-paperclip-1 bash -lc 'grep -n "\.clawsum-sidebar[^-]" /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css | head'

echo "=== gui.log recent ==="
docker exec clawsum-paperclip-1 tail -n 40 /paperclip/.hermes/logs/gui.log
