#!/usr/bin/env bash
# Install Hermes agent + Paperclip adapter inside the Paperclip container.
set -eu

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"

echo "Installing Hermes in ${CONTAINER}..."
docker exec -u root "${CONTAINER}" bash -lc '
  set -eu
  export DEBIAN_FRONTEND=noninteractive
  if ! command -v python3 >/dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv curl
  fi
  pip3 install --break-system-packages -q hermes-agent 2>/dev/null || pip3 install -q hermes-agent
  npm install -g hermes-paperclip-adapter 2>/dev/null || true
  command -v hermes && hermes --version || echo "hermes CLI check failed"
'

echo "Done. For dashboard: bash scripts/install-hermes-dashboard.sh && bash scripts/hermes-dashboard.sh start"
