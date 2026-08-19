#!/bin/bash
set -euo pipefail
ROOT=/docker/clawsum

# Stop hung client only — do not restart Postgres/containers
pkill -f 'provision-content-factory.sh' 2>/dev/null || true
pkill -f 'docker exec -i clawsum-postgres-1 psql' 2>/dev/null || true
sleep 1

echo "=== remaining schema (no \\c) ==="
docker exec -i clawsum-postgres-1 psql -U clawsum -d clawsum -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS ops.content_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,
  pack_id UUID REFERENCES ops.content_packs(id) ON DELETE SET NULL,
  kind TEXT NOT NULL,
  path TEXT,
  uri TEXT,
  media_object_id UUID,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT content_assets_kind_chk CHECK (
    kind IN ('flyer', 'image', 'first_frame', 'thumbnail', 'video', 'script', 'other')
  )
);
CREATE INDEX IF NOT EXISTS idx_content_assets_idea ON ops.content_assets (idea_id, kind);

CREATE TABLE IF NOT EXISTS ops.social_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,
  pack_id UUID REFERENCES ops.content_packs(id) ON DELETE SET NULL,
  platform TEXT NOT NULL,
  caption TEXT,
  scheduled_for TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'draft',
  approval_id UUID,
  posted_ref TEXT,
  error TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT social_queue_status_chk CHECK (
    status IN ('draft', 'pending_approval', 'approved', 'scheduled', 'posting', 'posted', 'failed', 'cancelled')
  )
);
CREATE INDEX IF NOT EXISTS idx_social_queue_status ON ops.social_queue (status, scheduled_for);
SQL

echo "=== openclaw content+social ==="
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
print("ok agents", len(agents))
PY

mkdir -p /docker/clawsum/data/.openclaw/workspace-content
mkdir -p /docker/clawsum/data/.openclaw/workspace-social
# lightweight seed if seed-persona not run
for ws in content social; do
  d=/docker/clawsum/data/.openclaw/workspace-$ws
  mkdir -p "$d"
  if [[ ! -f "$d/SOUL.md" ]]; then
    echo "# $ws agent — see docs/CONTENT-FACTORY.md" > "$d/SOUL.md"
  fi
done

bash /docker/clawsum/scripts/install-content-factory-cron.sh

echo "=== smoke ==="
python3 /docker/clawsum/scripts/content-factory.py daily --count 1
python3 /docker/clawsum/scripts/content-factory.py run-one

echo "=== verify ==="
docker exec clawsum-postgres-1 psql -U clawsum -d clawsum -c \
  "SELECT left(title,50), status FROM ops.content_ideas ORDER BY created_at DESC LIMIT 5;"
ls -la /docker/clawsum/data/media/exports/content/*/ 2>/dev/null | head -40
echo CONTENT_FACTORY_READY
