#!/usr/bin/env python3
from pathlib import Path
p = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist/provider-Cqe8M2zT.js')
lines = p.read_text(errors='replace').splitlines()
# print resolveDiscordGatewayIntents and call site
for i, line in enumerate(lines):
    if 'function resolveDiscordGatewayIntents' in line or 'resolveDiscordGatewayIntents({' in line:
        start = i
        end = min(len(lines), i + 80)
        print(f'===== around {i+1} =====')
        for j in range(start, end):
            print(f'{j+1}:{lines[j]}')
        print()
