#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
D="$R/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
mkdir -p "$D/dist" "$R/examples/hermes-cockpit/skins" /paperclip/.hermes/skins 2>/dev/null || true
cp -f /tmp/index.js "$D/dist/index.js"
cp -f /tmp/manifest.json "$D/manifest.json"
cp -f /tmp/clawsum.yaml "$R/examples/hermes-cockpit/skins/clawsum.yaml"
docker cp /tmp/index.js clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
docker cp /tmp/manifest.json clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/manifest.json
docker cp /tmp/clawsum.yaml clawsum-paperclip-1:/paperclip/.hermes/skins/clawsum.yaml
# Neutralize every user skin so Hermes cannot fall back to caduceus
docker exec -u root clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
import re
root = Path("/paperclip/.hermes/skins")
root.mkdir(parents=True, exist_ok=True)
src = Path("/paperclip/.hermes/skins/clawsum.yaml")
text = src.read_text(encoding="utf-8") if src.is_file() else ""
for name in ["clawsum","default","ares","mono","slate","daylight","warm-lightmode","poseidon","sisyphus","charizard"]:
    out = root / f"{name}.yaml"
    body = text or "name: {0}\nbanner_logo: \"CLAWSUM\"\nbanner_hero: \"\"\n".format(name)
    body = re.sub(r"(?m)^name:\s*.*$", f"name: {name}", body, count=1)
    out.write_text(body, encoding="utf-8")
    print("skin", out)
PY
bash "$R/scripts/hermes-dashboard.sh" stop || true
docker exec -u root clawsum-paperclip-1 bash -lc 'rm -f /paperclip/logs/hermes-dashboard.pid' || true
sleep 1
bash "$R/scripts/hermes-dashboard.sh" start
echo CHAT3D_CLEAN_APPLIED
