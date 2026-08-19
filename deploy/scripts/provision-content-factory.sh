#!/usr/bin/env bash
# Install content factory files, schema, cron. Patch openclaw.json in place (no compose restart).
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"

echo "=== schema ==="
# Strip any leftover \c so docker exec -i does not hang
sed '/^\\c /d' "$ROOT/postgres-init/20-ops-content-factory.sql" \
  | docker exec -i clawsum-postgres-1 psql -U clawsum -d clawsum -v ON_ERROR_STOP=1

echo "=== seed content + social workspaces ==="
# reuse seed-persona if present
if [[ -f "$ROOT/scripts/seed-persona-os.sh" ]]; then
  bash "$ROOT/scripts/seed-persona-os.sh" >/tmp/seed-persona-content.log 2>&1 || true
  tail -3 /tmp/seed-persona-content.log || true
fi

echo "=== openclaw.json content+social (no restart) ==="
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
cfg = json.loads(p.read_text())
agents = cfg.setdefault("agents", {}).setdefault("list", [])
want = {
    "content": {
        "id": "content",
        "name": "Content",
        "workspace": "/home/node/.openclaw/workspace-content",
        "tools": {"allow": ["read", "write", "edit", "exec"], "deny": []},
    },
    "social": {
        "id": "social",
        "name": "Social",
        "workspace": "/home/node/.openclaw/workspace-social",
        "tools": {"allow": ["read", "write", "edit"], "deny": ["exec"]},
    },
}
by = {a.get("id"): a for a in agents if isinstance(a, dict)}
for aid, entry in want.items():
    if aid in by:
        by[aid].update(entry)
        print("updated", aid)
    else:
        agents.append(entry)
        print("added", aid)
p.write_text(json.dumps(cfg, indent=2) + "\n")
print("wrote", p)
PY

echo "=== paperclip agents ==="
python3 "$ROOT/scripts/wire-paperclip-clawsum.py" 2>/dev/null | tail -20 || \
  python3 "$ROOT/scripts/wire-paperclip-clawsum.py" | tail -20 || true

echo "=== cron ==="
bash "$ROOT/scripts/install-content-factory-cron.sh"

echo "=== smoke daily + run-one ==="
python3 "$ROOT/scripts/content-factory.py" daily --count 1
python3 "$ROOT/scripts/content-factory.py" run-one

echo "CONTENT_FACTORY_READY"
