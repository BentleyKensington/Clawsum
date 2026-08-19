#!/usr/bin/env bash
set -euo pipefail
export PATH=/paperclip/.hermes-venv/bin:$PATH
cd /paperclip
echo "=== hermes config path ==="
hermes config path 2>&1 || true
hermes config env-path 2>&1 || true
echo "=== hermes config show ==="
hermes config show 2>&1 | head -120 || true
echo "=== env files ==="
ls -la /paperclip/.hermes/.env /paperclip/.env /paperclip/instances/default/.env 2>/dev/null || true
for f in /paperclip/.hermes/.env /paperclip/.env /home/node/.hermes/.env; do
  if [[ -f "$f" ]]; then
    echo "FILE $f keys:"; grep -E '^[A-Z0-9_]+=' "$f" | cut -d= -f1
  fi
done
echo "=== host .env openrouter? ==="
grep -E '^OPENROUTER' /docker/clawsum/.env | cut -d= -f1 || echo none
echo "=== recent session models ==="
python3 - <<'PY'
import sqlite3
c=sqlite3.connect('/paperclip/.hermes/state.db')
rows=c.execute("select id, model, billing_provider, started_at, title, handoff_error from sessions order by started_at desc limit 8").fetchall()
for r in rows: print(r)
msgs=c.execute("select role, substr(content,1,200) from messages where content like '%429%' or content like '%rate limit%' or content like '%unavailable%' order by id desc limit 5").fetchall()
print('ERR MSGS', msgs)
PY
