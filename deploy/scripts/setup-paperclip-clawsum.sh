#!/bin/bash
# Wire Clawsum company + OpenClaw gateway agents into Paperclip (local_trusted mode).
set -eo pipefail
cd /docker/clawsum

API="${PAPERCLIP_API:-http://127.0.0.1:3100/api}"
GW_URL="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:48166}"
GW_TOKEN=$(grep -E '^OPENCLAW_GATEWAY_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")

if [[ -z "$GW_TOKEN" ]]; then
  echo "ERROR: OPENCLAW_GATEWAY_TOKEN missing in .env"
  exit 1
fi

echo "Paperclip health:"
curl -sS "$API/health" | python3 -m json.tool || true

# Test gateway from paperclip container
echo "Gateway from paperclip container:"
docker exec clawsum-paperclip-1 curl -sS -o /dev/null -w "healthz=%{http_code}\n" "${GW_URL}/healthz" || true

echo ""
echo "=== Automated wiring ==="
echo "  python3 /docker/clawsum/scripts/wire-paperclip-clawsum.py"
echo "  bash /docker/clawsum/scripts/fix-paperclip-openclaw-protocol.sh   # required for OpenClaw 2026.5.x"
echo "  bash /docker/clawsum/scripts/install-hermes-in-paperclip.sh"
echo ""
echo "UI: ssh -L 3100:127.0.0.1:3100 clawsum  ->  http://localhost:3100"
echo "Gateway WS for adapters: ws://127.0.0.1:48166"
