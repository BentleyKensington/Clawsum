#!/usr/bin/env bash
set -eu
REQUEST_ID="${1:?usage: approve-openclaw-device-host.sh <requestId>}"
ENV_FILE="/docker/clawsum/.env"
TOKEN=$(grep -m1 '^OPENCLAW_GATEWAY_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r"'"'")
IMAGE="${OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:2026.6.10}"
docker run --rm --network host \
  -v /docker/clawsum/data/.openclaw:/home/node/.openclaw \
  -e HOME=/home/node \
  -e OPENCLAW_STATE_DIR=/home/node/.openclaw \
  -e OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json \
  -e OPENCLAW_GATEWAY_PORT=48166 \
  "$IMAGE" \
  node dist/index.js devices approve "$REQUEST_ID" --token "$TOKEN"
