#!/usr/bin/env python3
from pathlib import Path
root = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist')
for p in sorted(root.glob('*.js')):
    text = p.read_text(errors='replace')
    if 'GatewayIntentBits' not in text and 'messageContent' not in text:
        continue
    hits = []
    for i, line in enumerate(text.splitlines()):
        low = line.lower()
        if any(k in low for k in ('gatewayintent', 'messagecontent', 'guildmembers', 'guildpresences', 'intents:')):
            hits.append(f'{i+1}:{line.strip()[:180]}')
    if hits:
        print('FILE', p.name)
        print('\n'.join(hits[:50]))
        print('---')
