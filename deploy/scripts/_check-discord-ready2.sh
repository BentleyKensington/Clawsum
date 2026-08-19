#!/bin/bash
docker logs clawsum-openclaw-gateway-1 --since 3m 2>&1 | grep -iE 'discord|READY|timeout|4014|logged|error|intent|reconnect|startup-not' | tail -80
echo '==== file ===='
docker exec clawsum-openclaw-gateway-1 sh -lc 'grep -iE "timed out|startup-not|4014|disallowed|logged in|gateway error" /tmp/openclaw/openclaw-2026-08-04.log | tail -40'
echo '==== config intents ===='
python3 - <<'PY'
import json
from pathlib import Path
d=json.loads(Path('/docker/clawsum/data/.openclaw/openclaw.json').read_text())['channels']['discord']
print('intents', d.get('intents'))
print('users sample', list((d.get('guilds') or {}).values())[0].get('users') if d.get('guilds') else None)
PY
