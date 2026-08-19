#!/usr/bin/env bash
# Full Gmail inbox → Hermes: backfill ALL inbox messages, then review every one.
set -euo pipefail
ROOT=/docker/clawsum
cd "$ROOT"
mkdir -p data/reports data/inbox-reports

export GMAIL_SYNC_QUERY="${GMAIL_SYNC_QUERY_OVERRIDE:-in:inbox}"
# Pull a large slice of inbox (override via env if needed)
export GMAIL_BACKFILL_MAX="${GMAIL_BACKFILL_MAX_OVERRIDE:-5000}"

echo "[$(date -Is)] full inbox backfill start query=$GMAIL_SYNC_QUERY max=$GMAIL_BACKFILL_MAX"

python3 scripts/gmail_oauth_health.py

python3 scripts/gmail-sync.py --backfill

echo "[$(date -Is)] reviewing ALL inbox messages"
python3 scripts/gmail-inbox-review.py \
  --inbox-only \
  --all \
  --limit "${GMAIL_REVIEW_LIMIT:-10000}" \
  --markdown \
  --create-reminders \
  --report-dir data/inbox-reports

python3 - <<'PY'
from pathlib import Path
import psycopg2
env={}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    line=line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k,_,v=line.partition("=")
    env[k.strip()]=v.strip().strip('"').strip("'")
conn=psycopg2.connect(
    host="127.0.0.1", port=5432,
    dbname=env.get("POSTGRES_DB","clawsum"),
    user=env.get("POSTGRES_USER","clawsum"),
    password=env.get("POSTGRES_PASSWORD",""),
)
cur=conn.cursor()
cur.execute("SELECT COUNT(*) FROM ops.emails WHERE is_inbox")
inbox=cur.fetchone()[0]
cur.execute("""
  SELECT COUNT(*) FROM ops.emails e
  LEFT JOIN ops.email_reviews r ON r.email_id=e.id
  WHERE e.is_inbox AND r.id IS NULL
""")
missing=cur.fetchone()[0]
cur.execute("""
  SELECT COUNT(*) FROM ops.emails
  WHERE is_inbox AND (analysis_report IS NULL OR analysis_report='')
""")
no_report=cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM ops.emails WHERE is_inbox AND review_status='needs_boss'")
needs=cur.fetchone()[0]
print(f"inbox={inbox} missing_reviews={missing} no_analysis_report={no_report} needs_boss={needs}")
conn.close()
PY

echo "[$(date -Is)] full inbox pipeline ok — Hermes cockpit Inbox can read ops.email_reviews"
