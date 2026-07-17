#!/bin/bash
# Paperclip openclaw_gateway adapter ships PROTOCOL_VERSION=3; OpenClaw 2026.5.x requires 4.
# Patch in-container (tsx runs from src) until ghcr.io/paperclipai/paperclip:latest includes v4.
set -euo pipefail

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
ADAPTER="/app/packages/adapters/openclaw-gateway/src/server"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Container $CONTAINER not running"
  exit 1
fi

docker exec "$CONTAINER" sed -i 's/const PROTOCOL_VERSION = 3;/const PROTOCOL_VERSION = 4;/' \
  "$ADAPTER/execute.ts"

docker exec "$CONTAINER" sed -i 's/minProtocol: 3,/minProtocol: 4,/' "$ADAPTER/test.ts"
docker exec "$CONTAINER" sed -i 's/maxProtocol: 3,/maxProtocol: 4,/' "$ADAPTER/test.ts"

# OpenClaw 2026.5.x agent RPC rejects unknown root property `paperclip` (context is in message + env).
docker exec "$CONTAINER" sed -i '/agentParams\.paperclip = paperclipPayload;/d' \
  "$ADAPTER/execute.ts"

echo "Patched protocol 3 -> 4 in $CONTAINER"
docker exec "$CONTAINER" grep PROTOCOL_VERSION "$ADAPTER/execute.ts" | head -1
docker exec "$CONTAINER" grep minProtocol "$ADAPTER/test.ts" | head -1

echo "Restarting Paperclip..."
cd /docker/clawsum
docker compose --profile orchestration restart paperclip
echo "Done. Re-assign a task to Clawsum Admin and check heartbeat log (no protocol mismatch)."
