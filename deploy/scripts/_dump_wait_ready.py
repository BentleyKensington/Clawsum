#!/usr/bin/env python3
from pathlib import Path
p = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist/provider-Cqe8M2zT.js')
lines = p.read_text(errors='replace').splitlines()
for i, line in enumerate(lines):
    if 'async function waitForGatewayReady' in line or 'function waitForGatewayReady' in line:
        for j in range(i, min(len(lines), i+120)):
            print(f'{j+1}:{lines[j]}')
        break
