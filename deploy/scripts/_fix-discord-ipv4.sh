#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/docker/clawsum/data/.openclaw/openclaw.json')
cfg = json.loads(p.read_text())
d = cfg.setdefault('channels', {}).setdefault('discord', {})
# Prefer IPv4-friendly / simpler allowlist while debugging WS readiness
d['enabled'] = True
d['groupPolicy'] = 'allowlist'
# Enable guild members intent since portal has LIMITED flag on
intents = d.setdefault('intents', {})
intents['guildMembers'] = True
# MessageContent is always requested by the plugin; Presence left off unless needed
# Ensure account/default config picks this up if nested
guilds = d.get('guilds') or {}
for gid, gcfg in guilds.items():
    if isinstance(gcfg, dict):
        # keep requireMention false on free-respond channels already set
        gcfg['users'] = ['*']  # temporarily allow all guild members for reply test
cfg['channels']['discord'] = d
p.write_text(json.dumps(cfg, indent=2) + '\n')
print('updated discord intents + users=*')
PY

# Force IPv4-first for Node DNS in gateway
COMPOSE=/docker/clawsum/docker-compose.yml
if ! grep -q 'dns-result-order=ipv4first' "$COMPOSE"; then
  python3 - <<'PY'
from pathlib import Path
p = Path('/docker/clawsum/docker-compose.yml')
text = p.read_text()
needle = 'OPENCLAW_DISABLE_BONJOUR: "1"'
insert = 'OPENCLAW_DISABLE_BONJOUR: "1"\n      NODE_OPTIONS: "--dns-result-order=ipv4first"'
if needle in text and 'dns-result-order=ipv4first' not in text:
    text = text.replace(needle, insert, 1)
    p.write_text(text)
    print('compose: added NODE_OPTIONS ipv4first')
else:
    print('compose: unchanged')
PY
fi

cd /docker/clawsum
docker compose up -d --force-recreate openclaw-gateway
sleep 25
echo '==== status ===='
docker ps --filter name=clawsum-openclaw-gateway --format '{{.Names}} {{.Status}}'
echo '==== discord logs ===='
docker logs clawsum-openclaw-gateway-1 --since 40s 2>&1 | grep -iE 'discord|READY|timeout|4014|logged|error|intent|ipv4|reconnect' | tail -60
echo '==== TOKEN ===='
docker exec clawsum-openclaw-gateway-1 printenv DISCORD_BOT_TOKEN | wc -c
docker exec clawsum-openclaw-gateway-1 printenv NODE_OPTIONS || true
