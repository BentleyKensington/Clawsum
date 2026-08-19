#!/usr/bin/env bash
set -euo pipefail
echo "=== clawsum-runtime.env (keys only) ==="
cut -d= -f1 /docker/clawsum/paperclip-data/.hermes/clawsum-runtime.env 2>/dev/null || true
echo "=== .env keys related ==="
grep -E '^(OPENROUTER|OPENAI|ANTHROPIC|HERMES|LLM|MODEL)' /docker/clawsum/.env | cut -d= -f1 || true
echo "=== hermes state model ==="
docker exec clawsum-postgres-1 true 2>/dev/null || true
sqlite3 /docker/clawsum/paperclip-data/.hermes/state.db ".tables" 2>/dev/null || python3 - <<'PY'
import sqlite3
c=sqlite3.connect('/docker/clawsum/paperclip-data/.hermes/state.db')
print(c.execute("select name from sqlite_master where type='table'").fetchall())
for t in c.execute("select name from sqlite_master where type='table'").fetchall():
  name=t[0]
  try:
    cols=[r[1] for r in c.execute(f'pragma table_info({name})')]
    if any('model' in x.lower() or 'provider' in x.lower() or 'config' in x.lower() for x in cols):
      print('TABLE', name, cols)
      rows=c.execute(f'select * from {name} limit 5').fetchall()
      print(rows[:2])
  except Exception as e:
    print(name, e)
PY
echo "=== hermes CLI model ==="
docker exec clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes model --help 2>&1 | head -40; hermes config --help 2>&1 | head -40; ls /paperclip/.hermes-venv/bin | head'
echo "=== search default model in site-packages ==="
docker exec clawsum-paperclip-1 bash -lc 'grep -RIn --include="*.py" --include="*.yaml" -E "free-models-per-day|OPENROUTER|default_model|model_id" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes* 2>/dev/null | head -40'
