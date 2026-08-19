#!/usr/bin/env python3
"""Apply remaining schema via host psql on 127.0.0.1:5432 (avoid docker exec -i hang)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path("/docker/clawsum")
SQL_PATH = Path("/tmp/cf-rest.sql")

SQL = """
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
"""


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> int:
    load_env()
    # Write SQL inside the container without `docker exec -i` (hangs on this host).
    b64 = __import__("base64").b64encode(SQL.encode()).decode()
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "clawsum-postgres-1",
            "bash",
            "-lc",
            f"echo {b64} | base64 -d > /tmp/cf-rest.sql && psql -U clawsum -d clawsum -v ON_ERROR_STOP=1 -f /tmp/cf-rest.sql",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        return 1
    print("SCHEMA_OK")

    cfg_path = ROOT / "data/.openclaw/openclaw.json"
    cfg = json.loads(cfg_path.read_text())
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
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")

    for ws in ("content", "social"):
        d = ROOT / f"data/.openclaw/workspace-{ws}"
        d.mkdir(parents=True, exist_ok=True)
        soul = d / "SOUL.md"
        if not soul.is_file():
            soul.write_text(f"# {ws} — see docs/CONTENT-FACTORY.md\n", encoding="utf-8")

    subprocess.run(["bash", str(ROOT / "scripts/install-content-factory-cron.sh")], check=False)
    print(subprocess.check_output(["python3", str(ROOT / "scripts/content-factory.py"), "daily", "--count", "1"], text=True))
    print(subprocess.check_output(["python3", str(ROOT / "scripts/content-factory.py"), "run-one"], text=True, timeout=180))
    print("CONTENT_FACTORY_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
