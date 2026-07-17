#!/bin/bash
# Verify OpenClaw gateway + Telegram bindings (read-only checks on VPS).
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
GW="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:48166}"

echo "=== OpenClaw version ==="
docker exec clawsum-openclaw-gateway-1 node dist/index.js --version 2>/dev/null || echo "(version unavailable)"

echo ""
echo "=== Gateway health ==="
curl -sf "${GW}/healthz" && echo " OK" || { echo "FAIL"; exit 1; }

echo ""
echo "=== Agents in openclaw.json ==="
python3 - <<'PY'
import json
from pathlib import Path

p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
cfg = json.loads(p.read_text())
agents = cfg.get("agents", {}).get("list", [])
print(f"Listed agents: {len(agents)}")
ghl = []
for a in agents:
    if not isinstance(a, dict):
        continue
    aid = a.get("id", "?")
    print(f"  - {aid}")
    if str(aid).startswith("ghl-"):
        ghl.append(aid)
print(f"GHL account agents: {len(ghl)} → {', '.join(ghl) or 'none'}")
bindings = cfg.get("bindings", [])
print(f"Telegram bindings: {len(bindings)}")
for b in bindings:
    agent = b.get("agentId") if isinstance(b, dict) else b
    peer = b.get("peer", {}) if isinstance(b, dict) else {}
    title = peer.get("title") or peer.get("id") or "?"
    print(f"  - {agent} ← {title}")
PY

echo ""
echo "=== GHL Telegram bindings ==="
python3 /docker/clawsum/scripts/bind-ghl-telegram.py --status 2>/dev/null || echo "(bind-ghl-telegram unavailable)"

echo ""
echo "=== Telegram channel (gateway container) ==="
docker exec clawsum-openclaw-gateway-1 node dist/index.js channels status 2>/dev/null | head -25 || \
  echo "(channels status unavailable — check Control UI Telegram page)"

echo ""
echo "=== Manual smoke (Boss) ==="
echo "  1. Admin DM — @YourTelegramBot ping"
echo "  2. GHL group — @YourTelegramBot re-engage summary (ghl)"
echo "  3. Other specialist groups — one @mention each"
echo "Expect: one reply per binding; GHL agent reads REENGAGE.md (no search/browser)."
