#!/usr/bin/env python3
import os
from pathlib import Path
import psycopg2

env = {}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

conn = psycopg2.connect(
    host=env.get("POSTGRES_HOST", "127.0.0.1"),
    port=int(env.get("POSTGRES_PORT", "5432") or "5432"),
    user=env.get("POSTGRES_USER", "clawsum"),
    password=env.get("POSTGRES_PASSWORD", ""),
    dbname=env.get("POSTGRES_DB", "clawsum"),
)
cur = conn.cursor()
cur.execute(
    """
    WITH active AS (
      SELECT subject, object
      FROM ops.memory_facts
      WHERE status = 'active' AND scope <> 'personal'
        AND length(btrim(subject)) BETWEEN 2 AND 40
        AND length(btrim(object)) BETWEEN 2 AND 40
        AND cardinality(regexp_split_to_array(btrim(subject), %s)) <= 5
        AND cardinality(regexp_split_to_array(btrim(object), %s)) <= 5
    ),
    deg AS (
      SELECT label, COUNT(*)::int AS n
      FROM (
        SELECT subject AS label FROM active
        UNION ALL
        SELECT object FROM active
      ) x
      GROUP BY label
    )
    SELECT count(*) FROM deg
    """,
    ("\\s+", "\\s+"),
)
print("short_entity_labels", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM ops.memory_facts WHERE status='active' AND scope <> 'personal'")
print("active_biz_facts", cur.fetchone()[0])
conn.close()
