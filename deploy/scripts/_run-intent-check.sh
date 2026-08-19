#!/bin/bash
set -euo pipefail
python3 /tmp/_discord-app-intents.py
echo '==== log scan ===='
docker exec clawsum-openclaw-gateway-1 sh -lc '
  wc -l /tmp/openclaw/openclaw-2026-08-04.log
  grep -iE "timed out|startup-not|disallowed|4014|logged in|gateway ready|transport" /tmp/openclaw/openclaw-2026-08-04.log | tail -40
'
