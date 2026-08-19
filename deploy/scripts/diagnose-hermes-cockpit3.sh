#!/usr/bin/env bash
set -euo pipefail
echo "=== /api/dashboard/plugins ==="
curl -sS http://127.0.0.1:9119/api/dashboard/plugins | python3 -m json.tool | head -200

echo "=== grep web_server plugin auth / session ==="
docker exec clawsum-paperclip-1 bash -lc '
python3 - <<PY
from pathlib import Path
p=Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py")
text=p.read_text()
# print relevant snippets
keys=["dashboard/plugins","api/plugins","Unauthorized","session","auth_middleware","allowed_hosts","origin_mismatch","bundled","plugin_api","HERMES_HOME","plugins/"]
for i,line in enumerate(text.splitlines(),1):
  low=line.lower()
  if any(k.lower() in line for k in keys) or "require" in low and "auth" in low:
    if i<3500:
      print(f"{i}:{line[:160]}")
PY
'

echo "=== session token how ==="
docker exec clawsum-paperclip-1 bash -lc '
grep -n "session" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py | head -40
# try to get token from status or bootstrap
curl -sS -c /tmp/cj -b /tmp/cj http://127.0.0.1:9119/api/status >/dev/null
curl -sS -c /tmp/cj -b /tmp/cj -D- http://127.0.0.1:9119/api/dashboard/plugins 2>&1 | head -30
ls -la /tmp/cj; cat /tmp/cj
'

echo "=== bundled plugins path ==="
docker exec clawsum-paperclip-1 bash -lc '
ls /paperclip/.hermes-venv/lib/python3.13/site-packages/plugins/ | head
find /paperclip/.hermes-venv -path "*hermes-achievements*" | head
ls /paperclip/.hermes/plugins/
# how does discovery work
python3 - <<PY
from pathlib import Path
import hermes_cli.plugins as pl
print([x for x in dir(pl) if not x.startswith("_")])
PY
'
