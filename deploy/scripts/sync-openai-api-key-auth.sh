#!/bin/bash
# Register OPENAI_API_KEY from .env into all agent auth profiles (API-key fallback).
set -eo pipefail
cd /docker/clawsum
OPENAI_API_KEY=$(grep -E '^OPENAI_API_KEY=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY not set in .env"
  exit 1
fi
for agent in admin coding data realestate ghl comms research planning paperclip main; do
  echo "==> openai auth profile: $agent"
  printf '%s' "$OPENAI_API_KEY" | docker compose run --rm -T openclaw-cli \
    models auth --agent "$agent" paste-token --provider openai --profile-id openai:default 2>&1 | tail -5
done
echo "Done. Prefer Codex OAuth: docker compose run --rm openclaw-cli models auth login --provider openai-codex --device-code"
