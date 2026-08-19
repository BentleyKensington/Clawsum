#!/bin/bash
set -euo pipefail
echo '==== health ===='
docker exec clawsum-openclaw-gateway-1 sh -lc 'curl -s --max-time 5 http://127.0.0.1:18789/healthz || true; echo; curl -s --max-time 5 http://127.0.0.1:18789/api/channels || true; echo'
echo '==== notify nudge ===='
python3 /docker/clawsum/scripts/clawsum_notify.py "Clawsum: Discord 2-way should be live. Boss — reply hi in #boss-desk"
echo '==== watch note ===='
echo "Now watching logs for 60s — send hi in #boss-desk"
timeout 60 docker logs -f clawsum-openclaw-gateway-1 2>&1 | grep -iE 'discord|inbound|message|boss-desk|admin|agent|error|READY|timeout' || true
