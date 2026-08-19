#!/usr/bin/env bash
set -euo pipefail
LOG=/tmp/hermes-codex-oauth.log
rm -f "$LOG"
docker exec -u root clawsum-paperclip-1 bash -lc '
script -q -e -c "
export PATH=/paperclip/.hermes-venv/bin:\$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
export PYTHONUNBUFFERED=1
hermes auth add openai-codex --type oauth --no-browser --timeout 900
" /dev/null
' 2>&1 | tee "$LOG"
