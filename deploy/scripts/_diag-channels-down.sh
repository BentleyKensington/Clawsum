#!/usr/bin/env bash
set -euo pipefail
echo "=== containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -Ei 'openclaw|paperclip|traefik|hermes|minio|postgres' || docker ps --format 'table {{.Names}}\t{{.Status}}' | head -30

echo "=== gateway health ==="
curl -sS -m 5 -o /tmp/gw.json -w 'http:%{http_code}\n' http://127.0.0.1:48166/healthz || echo gw_fail
head -c 200 /tmp/gw.json 2>/dev/null; echo

echo "=== paperclip ==="
curl -sS -m 5 -o /dev/null -w '3100:%{http_code}\n' http://127.0.0.1:3100/api/health || echo pc_fail
systemctl is-active clawsum-paperclip-agent-proxy || true

echo "=== gateway logs (discord/telegram errors) ==="
docker logs clawsum-openclaw-gateway-1 --tail 120 2>&1 | grep -iE 'error|discord|telegram|disconnect|fatal|ECONN|unauthor|401|403|websocket|ready|logged' | tail -60

echo "=== channels env present (redacted) ==="
docker exec clawsum-openclaw-gateway-1 sh -c 'printenv | grep -E "^(DISCORD_|TELEGRAM_|OPENCLAW_)" | sed -E "s/=.*/=SET/"' || true

echo "=== openclaw channels config ==="
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/docker/clawsum/data/.openclaw/openclaw.json')
cfg=json.loads(p.read_text())
ch=cfg.get('channels') or {}
print('telegram.enabled', (ch.get('telegram') or {}).get('enabled'))
print('discord.enabled', (ch.get('discord') or {}).get('enabled'))
pl=(cfg.get('plugins') or {}).get('entries') or {}
for k in ('telegram','discord'):
    print(f'plugin.{k}', pl.get(k))
# bindings count
print('bindings', len(cfg.get('bindings') or []))
print('agents', len((cfg.get('agents') or {}).get('list') or []))
PY

echo "=== public probes ==="
for u in https://boss.clawsum.com/ https://paperclip.clawsum.com/ https://openclaw.clawsum.com/; do
  code=$(curl -sS -m 8 -o /dev/null -w '%{http_code}' -k "$u" || echo fail)
  echo "$u => $code"
done
