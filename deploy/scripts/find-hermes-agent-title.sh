#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
find /paperclip/.hermes-venv -type d \( -name dist -o -name web -o -name dashboard* \) 2>/dev/null | head -40
grep -RIn "Hermes Agent" /paperclip/.hermes-venv/lib/python3.13/site-packages --include="*.js" --include="*.mjs" --include="*.html" --include="*.json" 2>/dev/null | head -30
grep -RIn "agent_name\|Hermes Agent\|document.title" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli --include="*.py" 2>/dev/null | head -40
'
