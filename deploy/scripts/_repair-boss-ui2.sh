#!/usr/bin/env bash
set +u
set -eo pipefail
ROOT=/docker/clawsum
cd "$ROOT"
set -a; . ./.env; set +a

echo "=== apply chatgpt archive SQL if needed ==="
if [[ -f postgres-init/13-chatgpt-archive.sql ]]; then
  docker exec -i clawsum-postgres-1 env PGPASSWORD="$POSTGRES_PASSWORD" \
    psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -v ON_ERROR_STOP=1 \
    < postgres-init/13-chatgpt-archive.sql || true
fi
# also ensure businesses table exists (referenced by conversations)
docker exec -i clawsum-postgres-1 env PGPASSWORD="$POSTGRES_PASSWORD" \
  psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "SELECT to_regclass('ops.conversations') AS conversations, to_regclass('ops.session_briefs') AS briefs;"

echo "=== wire hermes-nocache into clawsum-boss router ==="
python3 - <<'PY'
from pathlib import Path
import re
p=Path('/docker/traefik/dynamic/clawsum-com.yml')
t=p.read_text()
# Find clawsum-boss middlewares block
m=re.search(r'(    clawsum-boss:\n(?:      .*\n)*?      middlewares:\n)((?:        - .*\n)+)', t)
if not m:
    raise SystemExit('clawsum-boss middlewares not found')
head, items = m.group(1), m.group(2)
if 'hermes-nocache' not in items:
    items = '        - hermes-nocache\n' + items
    t = t[:m.start()] + head + items + t[m.end():]
    p.write_text(t)
    print('added hermes-nocache to clawsum-boss')
else:
    print('already wired')
# show
for i,line in enumerate(t.splitlines(),1):
    if 'clawsum-boss' in line or (i>70 and i<100 and ('middleware' in line or 'hermes-' in line or 'rule:' in line)):
        print(f'{i}:{line}')
PY

echo "=== strengthen sidebar CSS contrast ==="
CSS=/docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css
python3 - <<'PY'
from pathlib import Path
p=Path('/docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/style.css')
t=p.read_text()
block='''
.clawsum-sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  width: 100%;
  min-width: 11rem;
  color: #e8eef4 !important;
  opacity: 1 !important;
  visibility: visible !important;
}
.clawsum-sidebar a,
.clawsum-sidebar .clawsum-sidebar-btn,
.clawsum-sidebar .clawsum-sidebar-btn-label {
  color: #e8eef4 !important;
}
.clawsum-sidebar .clawsum-sidebar-btn {
  background: rgba(15, 23, 42, 0.65) !important;
  border: 1px solid rgba(45, 212, 191, 0.45) !important;
}
'''
if '.clawsum-sidebar {' in t and 'min-width: 11rem' in t:
    print('sidebar base already strengthened')
else:
    # insert after first clawsum-sidebar-nav or at top of sidebar section
    needle='.clawsum-sidebar-nav {'
    if needle in t:
        t=t.replace(needle, block + '\n' + needle, 1)
    else:
        t = block + '\n' + t
    p.write_text(t)
    print('strengthened sidebar CSS')
PY

# sync css into all clawsum plugins + container
for name in clawsum-cockpit clawsum-inbox clawsum-agents clawsum-skills; do
  mkdir -p "$ROOT/examples/hermes-cockpit/plugin/$name/dashboard/dist"
  cp -f "$CSS" "$ROOT/examples/hermes-cockpit/plugin/$name/dashboard/dist/style.css"
done
docker cp "$CSS" clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css
for name in clawsum-inbox clawsum-agents clawsum-skills; do
  docker cp "$CSS" "clawsum-paperclip-1:/paperclip/.hermes/plugins/$name/dashboard/dist/style.css" 2>/dev/null || true
done

# ensure index.js with Session Startup Briefs is present
grep -q 'Session Startup Briefs' \
  /docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js \
  && docker cp /docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js \
       clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js

bash /docker/clawsum/scripts/force-restart-hermes-dashboard.sh
sleep 2
bash /docker/clawsum/scripts/ensure-hermes-runtime.sh

TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
echo "=== archive after SQL ==="
curl -sS -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/archive \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("ok",d.get("ok"),"briefs",d.get("session_briefs_count"),"drive",len(d.get("drive_forward") or []), "err",d.get("error"))'

echo "=== plugin js has sidebar + briefs ==="
docker exec clawsum-paperclip-1 grep -c 'Session Startup Briefs\|clawsum-sidebar-btn\|registerSlot(NAME, "sidebar"' \
  /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js

echo DONE
