#!/usr/bin/env bash
# Mount Closebot skill onto OpenClaw + Hermes runtimes (bypass Paperclip skill sync).
#
# Why: Paperclip openclaw_gateway adapter returns skill sync unsupported
#   supported:false / mode:unsupported / "This adapter does not implement skill sync yet."
# Company-level skills stay in Paperclip storage but are NOT pushed to the agent.
# Fix: copy skill into OpenClaw workspace skills + Hermes skills (filesystem mount).
#
# Env (edit with: ssh root@76.13.97.82 && nano /docker/clawsum/.env):
#   CLOSEBOT_API_KEY=...   # preferred → sent as HTTP header X-CB-KEY
#   X_CB_KEY=...           # fallback accepted by closebot_request.py
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC_REPO="$ROOT/skills/closebot-api-operator"
SRC_HERMES="$ROOT/paperclip-data/.hermes/skills/integrations/closebot-api-operator"
# Paperclip company skill copy (UUID folder) as alternate source
SRC_PC=$(find "$ROOT/paperclip-data/instances" -type d -name 'closebot-api-operator' 2>/dev/null | head -1 || true)
SRC="$SRC_REPO"
if [[ ! -f "$SRC/SKILL.md" ]]; then
  SRC="$SRC_HERMES"
fi
if [[ ! -f "$SRC/SKILL.md" && -n "${SRC_PC}" ]]; then
  SRC="$SRC_PC"
fi
if [[ ! -f "$SRC/SKILL.md" ]]; then
  echo "ERROR: closebot-api-operator skill not found under skills/, Hermes, or Paperclip instances" >&2
  exit 1
fi

OC_SKILLS="$ROOT/data/.openclaw/workspace/skills/closebot-api-operator"
HERMES_SKILLS="$ROOT/paperclip-data/.hermes/skills/integrations/closebot-api-operator"

mkdir -p "$(dirname "$OC_SKILLS")" "$(dirname "$HERMES_SKILLS")"
rsync -a --delete "$SRC/" "$OC_SKILLS/"
# OpenClaw gateway runs as uid 1000 (node) — must be readable
chown -R 1000:1000 "$ROOT/data/.openclaw/workspace/skills" 2>/dev/null || true
chmod -R u+rwX,go+rX "$ROOT/data/.openclaw/workspace/skills"
# Keep Hermes copy current too
if [[ "$SRC" != "$HERMES_SKILLS" ]]; then
  rsync -a --delete "$SRC/" "$HERMES_SKILLS/"
fi
chmod -R a+rX "$HERMES_SKILLS" 2>/dev/null || true
# Also inside paperclip container bind if distinct
if docker ps --format '{{.Names}}' | grep -q '^clawsum-paperclip-1$'; then
  docker exec clawsum-paperclip-1 mkdir -p /paperclip/.hermes/skills/integrations 2>/dev/null || true
  docker cp "$HERMES_SKILLS" clawsum-paperclip-1:/paperclip/.hermes/skills/integrations/closebot-api-operator 2>/dev/null || true
fi

echo "OK OpenClaw skill → $OC_SKILLS"
echo "OK Hermes skill  → $HERMES_SKILLS"

# Env check (do not print key)
if grep -qE '^CLOSEBOT_API_KEY=.+' "$ROOT/.env" 2>/dev/null || grep -qE '^X_CB_KEY=.+' "$ROOT/.env" 2>/dev/null; then
  echo "OK CLOSEBOT_API_KEY (or X_CB_KEY) present in $ROOT/.env"
else
  echo "WARN: add to $ROOT/.env then restart openclaw-gateway:"
  echo "  CLOSEBOT_API_KEY=your_key_here"
  echo "  # header used: X-CB-KEY"
fi

# Ensure gateway sees the var (compose already uses env_file: .env)
if docker ps --format '{{.Names}}' | grep -q openclaw-gateway; then
  if docker exec clawsum-openclaw-gateway-1 printenv CLOSEBOT_API_KEY >/dev/null 2>&1 \
     || docker exec clawsum-openclaw-gateway-1 printenv X_CB_KEY >/dev/null 2>&1; then
    echo "OK key visible inside openclaw-gateway container"
  else
    echo "WARN: key not in gateway container env — restart after editing .env:"
    echo "  cd $ROOT && docker compose up -d openclaw-gateway"
  fi
fi

echo
echo "Paperclip UI skill sync will still show unsupported for openclaw_gateway — that is expected."
echo "Agents use the filesystem skill under workspace/skills/closebot-api-operator instead."
