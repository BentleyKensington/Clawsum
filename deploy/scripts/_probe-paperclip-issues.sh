#!/usr/bin/env bash
set +u
COMPANY=97112442-5ced-44f2-afb8-dd5ee90145b9
API=http://127.0.0.1:3100/api
echo "=== dashboard ==="
curl -sS "$API/companies/$COMPANY/dashboard" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(sorted(d.keys()))'
echo "=== issues endpoints ==="
for p in \
  "/companies/$COMPANY/issues?limit=20" \
  "/companies/$COMPANY/tasks?limit=20" \
  "/companies/$COMPANY/issues?status=open&limit=20" \
  "/issues?companyId=$COMPANY&limit=10"
 do
  code=$(curl -sS -o /tmp/iss.json -w "%{http_code}" "$API$p" || echo err)
  echo "$code $p"
  python3 - <<'PY'
import json
from pathlib import Path
p=Path('/tmp/iss.json')
try:
  d=json.loads(p.read_text())
except Exception as e:
  print('parse',e); raise SystemExit
if isinstance(d, list):
  print(' list', len(d), 'sample', {k:d[0].get(k) for k in ('id','identifier','title','status','priority') if isinstance(d,list) and d} if d else None)
elif isinstance(d, dict):
  print(' keys', sorted(d.keys())[:20])
  items=d.get('issues') or d.get('tasks') or d.get('items') or d.get('data')
  if isinstance(items, list) and items:
    print(' n', len(items), 'sample', {k:items[0].get(k) for k in list(items[0].keys())[:12]})
PY
done
echo "=== inbox needs_boss count ==="
# via cockpit with token
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
curl -sS -H "X-Hermes-Session-Token: $TOKEN" \
  "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/inbox?view=needs_boss&limit=5" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("ok",d.get("ok"),"n",len(d.get("action_items") or d.get("email_analyses") or []))'
