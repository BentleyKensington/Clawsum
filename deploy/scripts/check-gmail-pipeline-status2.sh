#!/usr/bin/env bash
set -euo pipefail
ENV=/docker/clawsum/.env
PASS=$(grep -E '^POSTGRES_PASSWORD=' "$ENV" | cut -d= -f2- | tr -d '\r')
C=clawsum-postgres-1
run() { docker exec -e "PGPASSWORD=$PASS" "$C" psql -U clawsum -d clawsum -P pager=off -c "$1"; }

echo "=== latest emails ==="
run "SELECT id, left(coalesce(subject,''),55) AS subject, processing_status, review_status, received_at, synced_at FROM ops.emails ORDER BY coalesce(received_at, synced_at) DESC NULLS LAST LIMIT 10;"

echo "=== latest reviews ==="
run "SELECT id, email_id, review_status, priority, left(summary,70) AS summary, analyzed_at FROM ops.email_reviews ORDER BY analyzed_at DESC NULLS LAST LIMIT 10;"

echo "=== health ==="
run "SELECT
  (SELECT count(*) FROM ops.emails e WHERE NOT EXISTS (SELECT 1 FROM ops.email_reviews r WHERE r.email_id = e.id)) AS emails_without_review,
  (SELECT count(*) FROM ops.emails WHERE review_status = 'unreviewed') AS unreviewed_emails,
  (SELECT count(*) FROM ops.email_reviews WHERE review_status = 'needs_boss') AS needs_boss,
  (SELECT max(analyzed_at) FROM ops.email_reviews) AS last_review_at,
  (SELECT max(synced_at) FROM ops.emails) AS last_sync_at,
  (SELECT max(received_at) FROM ops.emails) AS newest_received;"

echo "=== pipeline ok ==="
grep 'pipeline ok' /docker/clawsum/data/reports/gmail-inbox-pipeline.log | tail -8
echo "=== oauth ==="
cat /docker/clawsum/data/reports/gmail-oauth-health.json
echo
date -u +'now=%Y-%m-%dT%H:%M:%SZ'
