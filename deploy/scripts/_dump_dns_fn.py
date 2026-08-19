#!/usr/bin/env python3
from pathlib import Path
p = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist/provider-Cqe8M2zT.js')
lines = p.read_text(errors='replace').splitlines()
for i, line in enumerate(lines):
    if 'function createDiscordDnsLookup' in line or 'DISCORD_GATEWAY_READY' in line or 'resolveDiscordGatewayReadyTimeoutMs' in line:
        for j in range(max(0,i-2), min(len(lines), i+40)):
            print(f'{j+1}:{lines[j]}')
        print('---')
