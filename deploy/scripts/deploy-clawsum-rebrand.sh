#!/usr/bin/env bash
# Deploy Clawsum rebrand: skin ASCII, SOUL, cockpit, marketing login/connect.
set -euo pipefail
ROOT=/docker/clawsum
SRC=$ROOT/examples/hermes-cockpit
CONTAINER=clawsum-paperclip-1

# Sync skin + SOUL + theme + plugin from examples
mkdir -p "$SRC/skins"
docker exec -u root "$CONTAINER" mkdir -p /paperclip/.hermes/skins
docker cp "$SRC/skins/clawsum.yaml" "$CONTAINER:/paperclip/.hermes/skins/clawsum.yaml"
docker cp "$SRC/SOUL.md" "$CONTAINER:/paperclip/.hermes/SOUL.md"

# Config: display.skin=clawsum
docker exec -u root "$CONTAINER" bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
python3 - <<PY
from pathlib import Path
import yaml
p=Path("/paperclip/.hermes/config.yaml")
data=yaml.safe_load(p.read_text()) if p.exists() else {}
if not isinstance(data, dict): data={}
dash=data.setdefault("dashboard", {})
if not isinstance(dash, dict):
  dash={}; data["dashboard"]=dash
dash["theme"]="clawsum-command"
disp=data.setdefault("display", {})
if not isinstance(disp, dict):
  disp={}; data["display"]=disp
disp["skin"]="clawsum"
pl=data.setdefault("plugins", {})
if not isinstance(pl, dict):
  pl={}; data["plugins"]=pl
en=pl.get("enabled")
if not isinstance(en, list):
  en=[]; pl["enabled"]=en
if "clawsum-cockpit" not in en:
  en.append("clawsum-cockpit")
p.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
print(p.read_text())
PY
'

bash "$ROOT/scripts/install-hermes-cockpit.sh"
bash "$ROOT/scripts/hermes-dashboard.sh" stop || true
sleep 1
bash "$ROOT/scripts/hermes-dashboard.sh" start

# Marketing site (login/connect + pages)
if [[ -d $ROOT/sites/clawsum-com ]]; then
  # copy already synced via scp from host before this script
  docker restart clawsum-marketing 2>/dev/null || docker restart "$(docker ps --format '{{.Names}}' | grep -i market | head -1)" || true
fi

echo "OK — Clawsum skin active. Hard-refresh chat UI."
