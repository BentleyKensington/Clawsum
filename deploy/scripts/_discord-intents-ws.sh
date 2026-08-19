#!/bin/bash
set -euo pipefail
docker exec clawsum-openclaw-gateway-1 python3 - <<'PY'
from pathlib import Path
root = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist')
for p in root.glob('*.js'):
    text = p.read_text(errors='replace')
    if 'GatewayIntentBits' in text or 'IntentsBitField' in text or 'messageContent' in text.lower():
        hits = []
        for i, line in enumerate(text.splitlines()):
            low = line.lower()
            if any(k in low for k in ('gatewayintent', 'messagecontent', 'guildmembers', 'presence', 'intents:')):
                hits.append(f'{i+1}:{line.strip()}')
        if hits:
            print('FILE', p.name)
            print('\n'.join(hits[:40]))
            print('---')
PY

echo '=== websocket probe ==='
docker exec clawsum-openclaw-gateway-1 node - <<'NODE'
const ws = new WebSocket('wss://gateway.discord.gg/?v=10&encoding=json');
ws.addEventListener('open', () => console.log('ws_open'));
ws.addEventListener('message', (ev) => { console.log('ws_msg', String(ev.data).slice(0,200)); ws.close(); process.exit(0); });
ws.addEventListener('error', (e) => { console.error('ws_err', e.message || e); process.exit(1); });
setTimeout(() => { console.error('ws_timeout'); process.exit(2); }, 10000);
NODE
