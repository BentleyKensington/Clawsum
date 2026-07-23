#!/usr/bin/env bash
# Install Clawsum Hermes cockpit theme + plugin into the Paperclip/Hermes container.
# Prerequisites: hermes-agent[web] installed; dashboard can be started after this.
set -euo pipefail

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${ROOT}/deploy/examples/hermes-cockpit"
# Flat VPS layout may copy examples under /docker/clawsum/examples/
if [[ ! -d "$SRC" ]]; then
  SRC="${ROOT}/examples/hermes-cockpit"
fi
if [[ ! -d "$SRC" ]]; then
  # Dev checkout path
  SRC="$(cd "$(dirname "$0")/../examples/hermes-cockpit" && pwd)"
fi

HERMES_HOME_IN_CT="${HERMES_HOME_IN_CT:-/paperclip/.hermes}"

echo "Source:    ${SRC}"
echo "Container: ${CONTAINER}"
echo "Hermes:    ${HERMES_HOME_IN_CT}"

if [[ ! -f "${SRC}/theme/clawsum-command.yaml" ]]; then
  echo "ERROR: cockpit theme not found at ${SRC}/theme/clawsum-command.yaml" >&2
  exit 1
fi

if ! docker inspect "${CONTAINER}" >/dev/null 2>&1; then
  echo "ERROR: container ${CONTAINER} not found" >&2
  exit 1
fi

docker exec -u root "${CONTAINER}" bash -lc "
  set -euo pipefail
  H='${HERMES_HOME_IN_CT}'
  mkdir -p \"\$H/dashboard-themes\" \"\$H/plugins\" \"\$H/clawsum-assets\"
  # Prefer /root/.hermes if hermes already created it
  if [[ -d /root/.hermes ]]; then
    H=/root/.hermes
    mkdir -p \"\$H/dashboard-themes\" \"\$H/plugins\" \"\$H/clawsum-assets\"
    echo \"Using Hermes home: \$H\"
  fi
  echo \"\$H\" > /tmp/clawsum-hermes-home
"

HERMES_HOME="$(docker exec "${CONTAINER}" cat /tmp/clawsum-hermes-home 2>/dev/null || echo "${HERMES_HOME_IN_CT}")"
echo "Resolved Hermes home: ${HERMES_HOME}"

# Theme
docker cp "${SRC}/theme/clawsum-command.yaml" \
  "${CONTAINER}:${HERMES_HOME}/dashboard-themes/clawsum-command.yaml"

# Plugin tree
docker exec -u root "${CONTAINER}" rm -rf "${HERMES_HOME}/plugins/clawsum-cockpit"
docker cp "${SRC}/plugin/clawsum-cockpit" \
  "${CONTAINER}:${HERMES_HOME}/plugins/clawsum-cockpit"

# Assets next to plugin API + shared dir
docker exec -u root "${CONTAINER}" mkdir -p \
  "${HERMES_HOME}/plugins/clawsum-cockpit/dashboard/assets" \
  "${HERMES_HOME}/clawsum-assets"
docker cp "${SRC}/assets/." \
  "${CONTAINER}:${HERMES_HOME}/plugins/clawsum-cockpit/dashboard/assets/"
docker cp "${SRC}/assets/." \
  "${CONTAINER}:${HERMES_HOME}/clawsum-assets/"

# Soft-link assets path used by plugin_api fallback
docker exec -u root "${CONTAINER}" bash -lc "
  ln -sfn '${HERMES_HOME}/clawsum-assets' /paperclip/.hermes/clawsum-assets 2>/dev/null || true
"

# Persist default theme if hermes config exists / create snippet
docker exec -u root "${CONTAINER}" bash -lc "
  set -euo pipefail
  H='${HERMES_HOME}'
  CFG=\"\$H/config.yaml\"
  if [[ -f \"\$CFG\" ]]; then
    if grep -q '^dashboard:' \"\$CFG\"; then
      if grep -q 'theme:' \"\$CFG\"; then
        sed -i 's/theme:.*/theme: clawsum-command/' \"\$CFG\" || true
      else
        printf '\n  theme: clawsum-command\n' >> \"\$CFG\"
      fi
    else
      printf '\ndashboard:\n  theme: clawsum-command\n' >> \"\$CFG\"
    fi
    echo \"Set dashboard.theme=clawsum-command in \$CFG\"
  else
    mkdir -p \"\$H\"
    printf 'dashboard:\n  theme: clawsum-command\n' > \"\$CFG\"
    echo \"Created \$CFG\"
  fi
"

echo ""
echo "OK Clawsum cockpit installed."
echo "Restart dashboard:"
echo "  bash ${ROOT}/scripts/hermes-dashboard.sh stop || true"
echo "  bash ${ROOT}/scripts/hermes-dashboard.sh start"
echo ""
echo "Then open Hermes UI → palette → 'Clawsum Command' (if not auto-selected)."
echo "Tab: Clawsum  |  Chat remains Hermes TUI."
echo ""
echo "Optional .env for data feeds (Paperclip container env):"
echo "  CLAWSUM_BOSS_URL=https://boss.yourdomain.com"
echo "  CLAWSUM_OPENCLAW_URL=https://clawsum.yourdomain.com"
echo "  CLAWSUM_GRAFANA_URL=https://grafana.yourdomain.com"
echo "  CLAWSUM_GRAFANA_EMBED_URL=https://grafana.yourdomain.com/d/clawsum-health?orgId=1&kiosk"
echo "  PAPERCLIP_API=http://127.0.0.1:3100/api"
echo "  PAPERCLIP_COMPANY_ID=..."
echo "  POSTGRES_PASSWORD=..."
echo ""
echo "Doc: deploy/examples/hermes-cockpit/README.md"
