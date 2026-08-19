#!/usr/bin/env python3
"""One-shot VPS snapshot for memory + Deepgram mail. Run on the VPS."""
from pathlib import Path

env = {}
p = Path("/docker/clawsum/.env")
if p.exists():
    for line in p.read_text(errors="replace").splitlines():
        if not line.strip() or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")

import psycopg2

conn = psycopg2.connect(
    host=env.get("POSTGRES_HOST", "127.0.0.1"),
    port=int(env.get("POSTGRES_PORT", "5432")),
    user=env.get("POSTGRES_USER", "clawsum"),
    password=env.get("POSTGRES_PASSWORD", ""),
    dbname=env.get("POSTGRES_DB", "clawsum"),
)
cur = conn.cursor()
queries = [
    "select status, count(*) from ops.memory_facts group by 1 order by 1",
    "select stage, max(started_at)::text, count(*) from ops.memory_dream_runs group by 1",
    "select count(*) from ops.emails where received_at >= current_date",
    "select count(*) from ops.conversations",
    "select count(*) from ops.conversations where coalesce(approved_for_hermes,false)",
]
for q in queries:
    try:
        cur.execute(q)
        print(q, "=>", cur.fetchall())
    except Exception as e:
        conn.rollback()
        print("FAIL", q, e)

try:
    cur.execute(
        """
        select received_at::text, left(coalesce(subject,''), 120), left(coalesce(from_addr,''), 80)
        from ops.emails
        where received_at >= current_date - interval '1 day'
          and (
            lower(coalesce(subject,'')) like '%deepgram%'
            or lower(coalesce(snippet,'')) like '%deepgram%'
            or lower(coalesce(from_addr,'')) like '%deepgram%'
          )
        order by received_at desc
        limit 15
        """
    )
    rows = cur.fetchall()
    print("deepgram_rows", rows or "NONE")
except Exception as e:
    conn.rollback()
    print("FAIL deepgram", e)
conn.close()
