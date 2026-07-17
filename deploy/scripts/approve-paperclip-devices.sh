#!/bin/bash
# Approve pending Paperclip/openclaw_gateway device pairing on the gateway.
set -euo pipefail
ENV_FILE="/docker/clawsum/.env"
TOKEN=$(grep -m1 '^OPENCLAW_GATEWAY_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r"'"'")
IMAGE="${OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:2026.6.10}"
# Gateway listens on 18789 inside the container; host maps 48166 -> 18789
GW_WS="ws://127.0.0.1:18789"
run() {
  docker run --rm --network "container:clawsum-openclaw-gateway-1" \
    -v /docker/clawsum/data/.openclaw:/home/node/.openclaw \
    -e HOME=/home/node \
    -e OPENCLAW_STATE_DIR=/home/node/.openclaw \
    -e OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json \
    "$IMAGE" \
    node dist/index.js "$@" --url "$GW_WS" --token "$TOKEN"
}
echo "Listing devices..."
run devices list 2>&1 || true
echo "Approving all pending (up to 20)..."
for _ in $(seq 1 20); do
  if ! run devices approve --latest 2>&1 | tee /tmp/oc-approve.log | grep -q "Approved\|approved\|paired"; then
    if grep -q "No pending" /tmp/oc-approve.log 2>/dev/null; then
      break
    fi
    # CLI may require explicit id
    REQ=$(grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' /tmp/oc-approve.log | head -1)
    if [[ -n "${REQ:-}" ]]; then
      run devices approve "$REQ" 2>&1 || break
    else
      break
    fi
  fi
done
run devices list 2>&1 || true
echo "Done."
