#!/bin/bash
set -euo pipefail
SRC=/docker/clawsum/examples/hermes-cockpit
# Files landed in /tmp/clawsum-flag as a directory or mixed — place what exists
if [[ -d /tmp/clawsum-flag ]]; then
  [[ -f /tmp/clawsum-flag/clawsum-command.yaml ]] && mv -f /tmp/clawsum-flag/clawsum-command.yaml "$SRC/theme/clawsum-command.yaml"
  [[ -f /tmp/clawsum-flag/clawsum.yaml ]] && mv -f /tmp/clawsum-flag/clawsum.yaml "$SRC/skins/clawsum.yaml"
  [[ -f /tmp/clawsum-flag/manifest.json ]] && mv -f /tmp/clawsum-flag/manifest.json "$SRC/plugin/clawsum-cockpit/dashboard/manifest.json"
  [[ -f /tmp/clawsum-flag/bg.svg ]] && cp -f /tmp/clawsum-flag/bg.svg "$SRC/assets/bg.svg" && cp -f /tmp/clawsum-flag/bg.svg "$SRC/plugin/clawsum-cockpit/dashboard/assets/bg.svg"
fi
python3 /tmp/_strip-yaml-bom.py \
  "$SRC/theme/clawsum-command.yaml" \
  "$SRC/skins/clawsum.yaml" || true
bash /docker/clawsum/scripts/install-clawsum-sidebar-plugins.sh
echo FLAG_THEME_DONE
