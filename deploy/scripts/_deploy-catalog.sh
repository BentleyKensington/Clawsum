#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
SRC=/tmp/clawsum-catalog
rsync -a "$SRC/plugin/" "$ROOT/examples/hermes-cockpit/plugin/"
bash "$ROOT/scripts/install-clawsum-sidebar-plugins.sh"
# quick API smoke inside container
docker exec -u root clawsum-paperclip-1 bash -lc '
python3 - <<PY
from pathlib import Path
p=Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py")
print("api_has_catalog", "/catalog" in p.read_text())
j=Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/authority.json")
import json
d=json.loads(j.read_text())
print("projects", len(d.get("projects") or []))
print("agents", len(d.get("agents") or []))
js=Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js").read_text()
print("ui_has_CatalogPanel", "CatalogPanel" in js)
PY
'
curl -sS -o /dev/null -w "hermes=%{http_code}\n" http://127.0.0.1:9119/ || true
echo CATALOG_DEPLOYED
