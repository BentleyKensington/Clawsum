#!/usr/bin/env python3
import subprocess
from pathlib import Path


def psql(sql: str) -> None:
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
    )
    print((proc.stdout or "") + (proc.stderr or ""))


print("=== imports ===")
psql(
    "SELECT id, import_status, conversation_count, original_filename, imported_at, "
    "left(coalesce(raw_archive_uri, ''), 100) AS uri "
    "FROM ops.chatgpt_imports ORDER BY imported_at DESC LIMIT 10;"
)
shards = Path("/docker/clawsum/data/chatgpt-archive/shards")
if shards.is_dir():
    names = sorted(p.name for p in shards.iterdir())
    print(f"shards_count={len(names)}")
    print("shards_sample=", names[:8])
print("=== recent conversations ===")
psql(
    "SELECT left(coalesce(title, ''), 60) AS title, scope, work_status, message_count "
    "FROM ops.conversations ORDER BY updated_at DESC NULLS LAST LIMIT 8;"
)
print("=== memory ===")
psql("SELECT count(*) AS chatgpt_memory_facts FROM ops.memory_facts WHERE source_kind = 'chatgpt';")
