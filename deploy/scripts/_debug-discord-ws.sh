#!/bin/bash
set -euo pipefail
docker exec clawsum-openclaw-gateway-1 sh -lc '
  find /home/node/.openclaw/npm/projects -maxdepth 3 -type d 2>/dev/null
  echo ---
  grep -R "awaiting gateway readiness" -n /home/node/.openclaw/npm/projects /app/dist 2>/dev/null | head -20
  echo ---
  grep -R "Message Content Intent" -n /home/node/.openclaw/npm/projects /app/dist 2>/dev/null | head -10
  echo ---
  node -e "fetch(\"https://discord.com/api/v10/gateway\").then(r=>r.json()).then(console.log).catch(console.error)"
'
echo --- logs ---
docker logs clawsum-openclaw-gateway-1 --since 5m 2>&1 | grep -iE 'discord|intent|disconn|error|ready|websocket|identify' | tail -40
