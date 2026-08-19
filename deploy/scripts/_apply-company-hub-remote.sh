#!/usr/bin/env bash
set -euo pipefail
S=/tmp/clawsum-hub
R=/docker/clawsum
cp -f "$S"/examples/hermes-cockpit/*.md "$R"/examples/hermes-cockpit/
mkdir -p "$R"/examples/hermes-cockpit/skins
cp -f "$S"/examples/hermes-cockpit/skins/clawsum.yaml "$R"/examples/hermes-cockpit/skins/
cp -f "$S"/examples/hermes-cockpit/plugin/_shared/clawsum-panels.js "$R"/examples/hermes-cockpit/plugin/_shared/
mkdir -p "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist
# scp often flattens dist/* into dashboard/
if [[ -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js ]]; then
  cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/
else
  cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/index.js "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js
fi
if [[ -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css ]]; then
  cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/
elif [[ -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/style.css ]]; then
  cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/style.css "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css
fi
cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/
cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/authority.json "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/
cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/manifest.json "$R"/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/
cp -f "$S"/examples/hermes-cockpit/plugin/clawsum-agents/dashboard/manifest.json "$R"/examples/hermes-cockpit/plugin/clawsum-agents/dashboard/
mkdir -p "$R"/personas
rm -rf "$R"/personas/clawsum
cp -a "$S"/personas/clawsum "$R"/personas/
sed -i 's/\r$//' "$S"/scripts/*.sh
install -m 0755 "$S"/scripts/seed-clawsum-company-pack.sh "$R"/scripts/
install -m 0755 "$S"/scripts/deploy-hermes-persona.sh "$R"/scripts/
install -m 0755 "$S"/scripts/install-clawsum-sidebar-plugins.sh "$R"/scripts/
cp -f "$S"/docs/*.md "$R"/docs/
cp -f "$S"/docker-compose.yml "$R"/docker-compose.yml
bash "$R"/scripts/install-clawsum-sidebar-plugins.sh
cd "$R"
docker compose --profile monitoring up -d grafana
echo CLAWSUM_HUB_DEPLOYED
