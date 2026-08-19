#!/bin/bash
docker exec clawsum-openclaw-gateway-1 python3 - <<'PY'
from pathlib import Path
p = Path('/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist/provider-Cqe8M2zT.js')
lines = p.read_text(errors='replace').splitlines()
for i, line in enumerate(lines[9800:9950], start=9801):
    print(f'{i}:{line}')
PY
