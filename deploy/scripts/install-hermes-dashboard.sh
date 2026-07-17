#!/usr/bin/env bash
# Install Nous Hermes Agent + web dashboard extras inside Paperclip container.
# Does NOT change Paperclip assignee adapter (still openclaw_gateway for Clawsum Hermes).
set -eu

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
LOG_DIR="${HERMES_LOG_DIR:-/paperclip/logs}"

echo "Installing Hermes Agent [web] in ${CONTAINER}..."
docker exec -u root "${CONTAINER}" bash -lc "
  set -eu
  export DEBIAN_FRONTEND=noninteractive
  if ! command -v python3 >/dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv curl
  fi
  VENV=/paperclip/.hermes-venv
  python3 -m venv \"\${VENV}\"
  \"\${VENV}/bin/pip\" install -q --upgrade pip
  \"\${VENV}/bin/pip\" install -q 'hermes-agent[web]'
  ln -sf \"\${VENV}/bin/hermes\" /usr/local/bin/hermes
  mkdir -p ${LOG_DIR}
  command -v hermes
  hermes --version || hermes version || true
"

echo ""
echo "OK Hermes CLI + web extras installed."
echo "Start dashboard: bash scripts/hermes-dashboard.sh start"
echo "Traefik route:   bash scripts/setup-ops-portal-traefik.sh (includes hermes.* host)"
echo ""
echo "Note: Clawsum Hermes assignee still uses openclaw_gateway (paperclip:hermes)."
echo "      Dashboard is for exploration / direct access — parallel to Boss UI."
