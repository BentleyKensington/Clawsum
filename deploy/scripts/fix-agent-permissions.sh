#!/usr/bin/env bash
# Fix uid 1000 (node) ownership on agent sessions + codex-home so Telegram + Codex work.
set -eu
BASE=/docker/clawsum/data/.openclaw
AGENTS=(admin coding data realestate ghl comms research planning paperclip)

echo "Fixing permissions under $BASE/agents ..."
for a in "${AGENTS[@]}"; do
  ad="$BASE/agents/$a"
  mkdir -p "$ad/sessions" "$ad/agent"
  chown -R 1000:1000 "$ad"
  chmod 700 "$ad/agent/auth-profiles.json" 2>/dev/null || true
  chmod -R u+rwX "$ad/sessions" "$ad/agent" 2>/dev/null || true
  echo "  $a: $(stat -c '%U:%G' "$ad/sessions")"
done

# Workspaces memory readable
for a in "${AGENTS[@]}"; do
  ws="$BASE/workspace-$a"
  [[ -d "$ws" ]] && chown -R 1000:1000 "$ws/memory" 2>/dev/null || true
done

echo "Done. Restarting gateway..."
cd /docker/clawsum
docker compose restart openclaw-gateway
sleep 10
docker exec clawsum-openclaw-gateway-1 curl -sS -o /dev/null -w "healthz=%{http_code}\n" http://127.0.0.1:18789/healthz
