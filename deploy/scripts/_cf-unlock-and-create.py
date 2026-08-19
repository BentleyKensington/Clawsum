#!/usr/bin/env python3
import subprocess


def psql(sql: str, timeout: int = 20) -> str:
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "clawsum-postgres-1",
            "psql",
            "-U",
            "clawsum",
            "-d",
            "clawsum",
            "-c",
            sql,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    print(proc.stdout or proc.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or "psql fail")
    return proc.stdout


# Drop our stuck DDL; also clear long idle-in-transaction blockers
psql(
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
    "WHERE pid <> pg_backend_pid() AND datname = 'clawsum' "
    "AND (query ILIKE '%content_assets%' OR query ILIKE '%social_queue%' "
    "OR (state = 'idle in transaction' AND xact_start < now() - interval '10 minutes'));"
)

psql(
    "CREATE TABLE IF NOT EXISTS ops.content_assets ("
    "id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    "created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
    "idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,"
    "pack_id UUID REFERENCES ops.content_packs(id) ON DELETE SET NULL,"
    "kind TEXT NOT NULL,"
    "path TEXT, uri TEXT, media_object_id UUID,"
    "meta JSONB NOT NULL DEFAULT '{}'::jsonb,"
    "CONSTRAINT content_assets_kind_chk CHECK ("
    "kind IN ('flyer','image','first_frame','thumbnail','video','script','other')));"
)
psql("CREATE INDEX IF NOT EXISTS idx_content_assets_idea ON ops.content_assets (idea_id, kind);")
psql(
    "CREATE TABLE IF NOT EXISTS ops.social_queue ("
    "id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    "created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
    "updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
    "idea_id UUID NOT NULL REFERENCES ops.content_ideas(id) ON DELETE CASCADE,"
    "pack_id UUID REFERENCES ops.content_packs(id) ON DELETE SET NULL,"
    "platform TEXT NOT NULL, caption TEXT, scheduled_for TIMESTAMPTZ,"
    "status TEXT NOT NULL DEFAULT 'draft', approval_id UUID, posted_ref TEXT, error TEXT,"
    "meta JSONB NOT NULL DEFAULT '{}'::jsonb,"
    "CONSTRAINT social_queue_status_chk CHECK (status IN "
    "('draft','pending_approval','approved','scheduled','posting','posted','failed','cancelled')));"
)
psql("CREATE INDEX IF NOT EXISTS idx_social_queue_status ON ops.social_queue (status, scheduled_for);")
psql(
    "SELECT tablename FROM pg_tables WHERE schemaname='ops' "
    "AND (tablename LIKE 'content%' OR tablename='social_queue') ORDER BY 1;"
)
print("TABLES_OK")
