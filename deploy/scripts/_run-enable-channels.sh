#!/usr/bin/env bash
set -euo pipefail
sed -i 's/\r$//' /tmp/_fix-enable-discord-telegram.py /tmp/configure-openclaw.py
cp -f /tmp/configure-openclaw.py /docker/clawsum/scripts/
python3 /tmp/_fix-enable-discord-telegram.py
chown 1000:1000 /docker/clawsum/data/.openclaw/openclaw.json
cd /docker/clawsum
docker compose up -d --force-recreate openclaw-gateway
for i in $(seq 1 20); do
  st=$(docker inspect -f '{{.State.Health.Status}}' clawsum-openclaw-gateway-1 2>/dev/null || echo starting)
  echo "status=$st"
  if [ "$st" = "healthy" ]; then
    break
  fi
  sleep 2
done
docker ps --filter name=clawsum-openclaw-gateway --format '{{.Names}} {{.Status}}'
echo "--- config ---"
python3 - <<'PY'
import json
from pathlib import Path
c = json.loads(Path("/docker/clawsum/data/.openclaw/openclaw.json").read_text())
print(
    "tg",
    c["channels"]["telegram"].get("enabled"),
    "dc",
    c["channels"]["discord"].get("enabled"),
    "pl_tg",
    c["plugins"]["entries"].get("telegram"),
    "pl_dc",
    c["plugins"]["entries"].get("discord"),
)
PY
echo "--- logs ---"
docker logs clawsum-openclaw-gateway-1 --tail 120 2>&1 \
  | grep -iE 'discord|telegram|ready|error|logged|connect|gateway|plugin' \
  | tail -40
echo "DONE"
