#!/usr/bin/env bash
set -euo pipefail
TOKEN=$(cat /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
# force reload? restart dashboard briefly if needed
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/inbox | tee /tmp/inbox-full.json | python3 -m json.tool | head -40
echo '==== plugin_api marker ===='
grep -n '_load_runtime_env\|psycopg2\|clawsum-runtime' /docker/clawsum/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py | head -20
echo '==== runtime env keys ===='
cut -d= -f1 /docker/clawsum/paperclip-data/.hermes/clawsum-runtime.env
ls -la /docker/clawsum/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env
echo '==== import test in hermes venv ===='
docker exec clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; python3 - <<"PY"
import sys
sys.path.insert(0, "/paperclip/.hermes/plugins/clawsum-cockpit/dashboard")
import plugin_api as p
print("env POSTGRES_USER", repr(p._env("POSTGRES_USER")))
print("env POSTGRES_HOST", repr(p._env("POSTGRES_HOST")))
print("password set", bool(p._env("POSTGRES_PASSWORD")))
try:
  import psycopg2
  print("psycopg2 ok", psycopg2.__version__)
except Exception as e:
  print("psycopg2 fail", e)
# call inbox handler
resp = p.inbox(limit=5)
# JSONResponse
body = resp.body if hasattr(resp, "body") else None
import json
if body:
  d=json.loads(body)
  print("inbox handler", d.get("ok"), d.get("error"), len(d.get("action_items") or []))
else:
  print("resp", resp)
PY'
