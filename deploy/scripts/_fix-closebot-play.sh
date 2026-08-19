#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
OC="$ROOT/data/.openclaw/workspace/skills/closebot-api-operator"
# OpenClaw runs as node (uid 1000) — skill was copied as root 600
chown -R 1000:1000 "$ROOT/data/.openclaw/workspace/skills" 2>/dev/null || true
chmod -R u+rwX,go+rX "$ROOT/data/.openclaw/workspace/skills"
# Hermes side readable too
chmod -R a+rX "$ROOT/paperclip-data/.hermes/skills/integrations/closebot-api-operator" 2>/dev/null || true

cd "$ROOT"
# Recreate gateway so it reloads .env (CLOSEBOT was added after last recreate)
docker compose up -d --force-recreate openclaw-gateway
sleep 4

echo "=== gateway env ==="
docker exec clawsum-openclaw-gateway-1 python3 -c '
import os
for k in ("CLOSEBOT_API_KEY","X_CB_KEY","OPENAI_API_KEY"):
  v=os.environ.get(k) or ""
  print(("SET" if len(v)>8 else "EMPTY"), k, "len", len(v))
'
echo "=== skill readable ==="
docker exec -u node clawsum-openclaw-gateway-1 ls -la /home/node/.openclaw/workspace/skills/closebot-api-operator/
docker exec -u node clawsum-openclaw-gateway-1 head -5 /home/node/.openclaw/workspace/skills/closebot-api-operator/SKILL.md

echo "=== closebot ping ==="
docker exec -u node clawsum-openclaw-gateway-1 python3 \
  /home/node/.openclaw/workspace/skills/closebot-api-operator/scripts/closebot_request.py \
  GET /agency/current 2>&1 | head -40

echo DONE
