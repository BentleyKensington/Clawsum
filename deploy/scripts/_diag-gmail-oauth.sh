#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
cd "$ROOT"
set -a; set +u; . .env; set -u; set +a

echo "=== health json ==="
cat data/reports/gmail-oauth-health.json 2>/dev/null || echo "(none)"
echo

echo "=== gmail_oauth_health.py ==="
python3 scripts/gmail_oauth_health.py 2>&1 || true
echo "exit=$?"

echo "=== token refresh probe ==="
python3 <<'PY'
import os, json
from pathlib import Path
env={}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    line=line.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    k,_,v=line.partition("=")
    env[k.strip()]=v.strip().strip('"').strip("'")
env.update({k:v for k,v in os.environ.items() if v})
missing=[k for k in ("GMAIL_CLIENT_ID","GMAIL_CLIENT_SECRET","GMAIL_REFRESH_TOKEN") if not env.get(k)]
print("missing", missing or "none")
print("client_id", (env.get("GMAIL_CLIENT_ID") or "")[:40]+"...")
print("refresh_len", len(env.get("GMAIL_REFRESH_TOKEN") or ""))
print("mailbox", env.get("GMAIL_ADMIN_ADDRESS"))
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except Exception as e:
    print("import_fail", e); raise SystemExit(1)
creds=Credentials(
    token=None,
    refresh_token=env["GMAIL_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=env["GMAIL_CLIENT_ID"],
    client_secret=env["GMAIL_CLIENT_SECRET"],
    scopes=["https://www.googleapis.com/auth/gmail.readonly"],
)
try:
    creds.refresh(Request())
    print("REFRESH_OK token_len", len(creds.token or ""))
    svc=build("gmail","v1",credentials=creds,cache_discovery=False)
    profile=svc.users().getProfile(userId="me").execute()
    print("PROFILE_OK", profile.get("emailAddress"), "messagesTotal", profile.get("messagesTotal"))
except Exception as e:
    print("REFRESH_FAIL", type(e).__name__, e)
    # dig into google errors
    err=getattr(e, "error", None) or getattr(e, "args", None)
    print("detail", err)
PY

echo "=== last sync / cron ==="
ls -lt /var/log/clawsum*gmail* 2>/dev/null | head || true
grep -RIl gmail /etc/cron* /docker/clawsum/cron* 2>/dev/null | head || true
crontab -l 2>/dev/null | grep -i gmail || true
ls -lt /docker/clawsum/data/reports/ 2>/dev/null | head
tail -40 /docker/clawsum/data/reports/gmail-inbox-pipeline.log 2>/dev/null || true
tail -40 /docker/clawsum/logs/gmail*.log 2>/dev/null || true

echo "=== recent emails sync state ==="
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -c \
  "SELECT last_sync_at, messages_total, backfill_completed FROM ops.email_sync_state; SELECT count(*) AS emails, max(synced_at) AS last_synced FROM ops.emails;"
echo DONE
