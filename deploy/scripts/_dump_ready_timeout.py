#!/usr/bin/env python3
from pathlib import Path
p = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist/provider-Cqe8M2zT.js')
lines = p.read_text(errors='replace').splitlines()
for start in (9480, 9560, 10180, 5780):
    print(f'===== {start+1}-{start+80} =====')
    for j in range(start, min(len(lines), start+80)):
        print(f'{j+1}:{lines[j]}')
    print()
