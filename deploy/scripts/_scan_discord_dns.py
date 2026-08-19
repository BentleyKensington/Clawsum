#!/usr/bin/env python3
from pathlib import Path
root = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist')
for p in sorted(root.glob('*.js')):
    text = p.read_text(errors='replace')
    if 'discordDnsLookup' not in text and 'guildMembers' not in text:
        continue
    lines = text.splitlines()
    interesting = []
    for i, line in enumerate(lines):
        if any(k in line for k in ('discordDnsLookup', 'guildMembers', 'gatewayReady', 'logged in to discord', 'DisallowedIntents')):
            interesting.append((i, line.strip()[:200]))
    if interesting:
        print('FILE', p.name)
        for i, line in interesting[:60]:
            print(f'{i+1}:{line}')
        print('---')
