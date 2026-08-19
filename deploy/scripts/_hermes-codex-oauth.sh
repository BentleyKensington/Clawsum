#!/usr/bin/env bash
# Start Hermes openai-codex OAuth (device code / manual-paste).
# Prints the URL + user code; waits for approval with a long timeout.
set -euo pipefail
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
HERMES_HOME=/paperclip/.hermes

docker exec -u root \
  -e HERMES_HOME="$HERMES_HOME" \
  -e HOME=/paperclip \
  -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin \
  "$CONTAINER" \
  hermes auth add openai-codex --type oauth --no-browser --timeout 300 2>&1
