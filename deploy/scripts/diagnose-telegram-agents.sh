#!/usr/bin/env bash
set -eu
BASE=/docker/clawsum/data/.openclaw
TODAY=$(TZ=America/Chicago date +%Y-%m-%d)
echo "Chicago today: $TODAY"

for a in admin coding data realestate ghl comms research planning paperclip; do
  echo "=== agent: $a ==="
  mem="$BASE/workspace-${a}/memory/${TODAY}.md"
  if [[ -f "$mem" ]]; then
    echo "memory OK: $mem"
  else
    echo "memory MISSING: $mem"
  fi
  auth="$BASE/agents/${a}/agent/auth-profiles.json"
  if [[ -f "$auth" ]]; then
    ls -la "$auth"
    python3 -c "import json; d=json.load(open('$auth')); print('profiles:', list(d.get('profiles',{}).keys())[:5])"
  else
    echo "auth MISSING: $auth"
  fi
done

echo "=== recent gateway errors ==="
docker exec clawsum-openclaw-gateway-1 sh -c 'grep -i error /tmp/openclaw/openclaw-2026-05-21.log 2>/dev/null | tail -30' || true
docker exec clawsum-openclaw-gateway-1 sh -c 'grep -i error /tmp/openclaw/openclaw-2026-05-22.log 2>/dev/null | tail -30' || true
