#!/usr/bin/env python3
from pathlib import Path
p = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist/provider-Cqe8M2zT.js')
lines = p.read_text(errors='replace').splitlines()
# imports at top + Agent usage
for i, line in enumerate(lines[:80]):
    if 'Agent' in line or 'import' in line and ('ws' in line or 'undici' in line or 'https' in line):
        print(f'{i+1}:{line}')
print('---')
for i, line in enumerate(lines):
    if 'from "ws"' in line or "from 'ws'" in line or 'Agent' in line and ('import' in line or 'require' in line):
        print(f'{i+1}:{line}')
# also search createNodeProxyAgent / undici
for i, line in enumerate(lines):
    if 'createNodeProxyAgent' in line or 'undici' in line.lower() or 'https-proxy' in line.lower():
        if i < 100 or 'Agent' in line:
            print(f'X{i+1}:{line[:180]}')
