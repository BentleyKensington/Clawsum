#!/usr/bin/env python3
"""Probe ChatGPT archive upload/import status on VPS."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path("/docker/clawsum")
ARCH = ROOT / "data" / "chatgpt-archive"


def psql(sql: str) -> str:
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
    out = (proc.stdout or "") + (proc.stderr or "")
    return out.strip()


print("=== archive files ===")
if ARCH.is_dir():
    files = sorted(ARCH.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[:30]:
        if p.is_file():
            print(f"{p.stat().st_size:12d}  {p.name}")
        else:
            print(f"{'DIR':>12}  {p.name}/")
    print(f"total_entries={len(files)}")
else:
    print("MISSING", ARCH)

print("\n=== ops.chatgpt_imports ===")
print(
    psql(
        "SELECT id, import_status, conversation_count, created_at, "
        "left(coalesce(source_path, ''), 80) AS source_path "
        "FROM ops.chatgpt_imports ORDER BY created_at DESC LIMIT 15;"
    )
)

print("\n=== conversation / message counts ===")
print(psql("SELECT count(*) AS conversations FROM ops.conversations;"))
print(psql("SELECT count(*) AS messages FROM ops.messages;"))
print(psql("SELECT scope, count(*) FROM ops.conversations GROUP BY 1 ORDER BY 2 DESC;"))
print(
    psql(
        "SELECT work_status, count(*) FROM ops.conversations GROUP BY 1 ORDER BY 2 DESC;"
    )
)

print("\n=== classify / hermes gates ===")
print(
    psql(
        "SELECT "
        "count(*) FILTER (WHERE scope IS NOT NULL AND scope <> 'unknown') AS scoped, "
        "count(*) FILTER (WHERE coalesce(scope, 'unknown') = 'unknown') AS unknown_scope, "
        "count(*) FILTER (WHERE approved_for_hermes) AS approved_hermes "
        "FROM ops.conversations;"
    )
)

print("\n=== memory facts from chatgpt ===")
print(
    psql(
        "SELECT count(*) FROM ops.memory_facts WHERE source_kind = 'chatgpt';"
    )
)

print("\n=== recent audit ===")
print(
    psql(
        "SELECT created_at, action, actor, left(coalesce(detail::text, ''), 120) "
        "FROM ops.audit_logs "
        "WHERE action ILIKE '%archive%' OR actor ILIKE '%chatgpt%' "
        "ORDER BY created_at DESC LIMIT 10;"
    )
)
