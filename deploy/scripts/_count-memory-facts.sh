#!/bin/bash
set -euo pipefail
# Find a container that actually has psql.
for name in $(docker ps --format '{{.Names}}'); do
  if docker exec "$name" sh -lc 'command -v psql' >/dev/null 2>&1; then
    echo "using $name"
    docker exec "$name" psql -U clawsum -d clawsum -At -c "SELECT 'active_biz=' || count(*) FILTER (WHERE status = 'active' AND scope <> 'personal') || ' all=' || count(*) || ' active=' || count(*) FILTER (WHERE status = 'active') FROM ops.memory_facts;"
    docker exec "$name" psql -U clawsum -d clawsum -At -c "SELECT 'uniq_subj=' || count(DISTINCT subject) || ' uniq_obj=' || count(DISTINCT object) FROM ops.memory_facts WHERE status = 'active' AND scope <> 'personal';"
    exit 0
  fi
done
echo "no psql in running containers; trying python"
python3 - <<'PY'
import os
from pathlib import Path
env = {}
p = Path("/docker/clawsum/.env")
if p.exists():
    for line in p.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
import psycopg2
conn = psycopg2.connect(
    host=env.get("POSTGRES_HOST", "127.0.0.1"),
    port=int(env.get("POSTGRES_PORT", "5432") or "5432"),
    user=env.get("POSTGRES_USER", "clawsum"),
    password=env.get("POSTGRES_PASSWORD", ""),
    dbname=env.get("POSTGRES_DB", "clawsum"),
)
cur = conn.cursor()
cur.execute(
    "SELECT count(*) FILTER (WHERE status='active' AND scope <> 'personal'), count(*), count(*) FILTER (WHERE status='active') FROM ops.memory_facts"
)
a, b, c = cur.fetchone()
print(f"active_biz={a} all={b} active={c}")
cur.execute(
    "SELECT count(DISTINCT subject), count(DISTINCT object) FROM ops.memory_facts WHERE status='active' AND scope <> 'personal'"
)
s, o = cur.fetchone()
print(f"uniq_subj={s} uniq_obj={o}")
conn.close()
PY
