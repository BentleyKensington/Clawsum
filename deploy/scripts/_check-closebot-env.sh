#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-openclaw-gateway-1 python3 -c 'import os; v=os.environ.get("CLOSEBOT_API_KEY") or os.environ.get("X_CB_KEY") or ""; print("KEY_NONEMPTY" if len(v)>8 else "KEY_EMPTY_OR_MISSING", "len", len(v))'
grep -E '^CLOSEBOT_API_KEY=|^X_CB_KEY=' /docker/clawsum/.env 2>/dev/null | sed 's/=.*/=***/' || echo 'no CLOSEBOT line in .env'
ls /docker/clawsum/data/.openclaw/workspace/skills/closebot-api-operator/scripts/
