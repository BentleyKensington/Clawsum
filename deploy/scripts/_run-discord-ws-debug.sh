#!/bin/bash
set -euo pipefail
docker cp /tmp/_scan_discord_intents.py clawsum-openclaw-gateway-1:/tmp/
docker exec clawsum-openclaw-gateway-1 python3 /tmp/_scan_discord_intents.py | head -100
cat >/tmp/_ws_probe.js <<'JS'
const ws = new WebSocket('wss://gateway.discord.gg/?v=10&encoding=json');
ws.addEventListener('open', () => console.log('ws_open'));
ws.addEventListener('message', (e) => {
  console.log('ws_msg', String(e.data).slice(0, 160));
  ws.close();
  process.exit(0);
});
ws.addEventListener('error', () => {
  console.error('ws_err');
  process.exit(1);
});
setTimeout(() => {
  console.error('ws_timeout');
  process.exit(2);
}, 10000);
JS
docker cp /tmp/_ws_probe.js clawsum-openclaw-gateway-1:/tmp/_ws_probe.js
echo '===WS==='
docker exec clawsum-openclaw-gateway-1 node /tmp/_ws_probe.js
echo '===STATUS==='
docker logs clawsum-openclaw-gateway-1 2>&1 | grep -i 'logged in to discord\|awaiting gateway\|DisallowedIntents\|4014' | tail -20
