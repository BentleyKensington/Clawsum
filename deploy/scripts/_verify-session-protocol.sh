#!/usr/bin/env bash
set -euo pipefail
bash /docker/clawsum/scripts/deploy-hermes-persona.sh
echo "=== BOOT ==="
sed -n '1,40p' /paperclip/.hermes/BOOT.md 2>/dev/null || docker exec -u root clawsum-paperclip-1 sed -n '1,40p' /paperclip/.hermes/BOOT.md
echo "=== SOUL session block ==="
docker exec -u root clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
for name in ("BOOT.md","SOUL.md","WORKFLOWS.md","LAST_SESSION.md"):
    p = Path("/paperclip/.hermes")/name
    t = p.read_text() if p.exists() else ""
    print(name, "bytes", len(t))
    for needle in ("returns after idle", "not enough data", "Unique greeting", "Next actions", "Session Startup Brief"):
        print(" ", needle, "YES" if needle.lower() in t.lower() else "no")
PY
