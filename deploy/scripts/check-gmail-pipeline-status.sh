#!/usr/bin/env bash
set -euo pipefail
echo "=== crontab (gmail/inbox) ==="
crontab -l 2>/dev/null | grep -iE 'gmail|inbox' || echo "(none in root crontab)"
echo
echo "=== cron.d ==="
ls -la /etc/cron.d/*gmail* /etc/cron.d/*clawsum* 2>/dev/null || echo "(none)"
echo
echo "=== pipeline log (tail) ==="
tail -n 40 /docker/clawsum/data/reports/gmail-inbox-pipeline.log 2>/dev/null || echo "(no pipeline log)"
echo
echo "=== sync log (tail) ==="
tail -n 20 /docker/clawsum/data/reports/gmail-sync.log 2>/dev/null || echo "(no sync log)"
echo
echo "=== oauth health ==="
cat /docker/clawsum/data/reports/gmail-oauth-health.json 2>/dev/null || echo "(none)"
echo
echo "=== DB: recent emails + reviews ==="
# shellcheck disable=SC1091
set +u
source /docker/clawsum/.env 2>/dev/null || true
set -u
export PGPASSWORD="${POSTGRES_PASSWORD:-}"
PSQL=(docker exec -e PGPASSWORD="$PGPASSWORD" clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -t -A)
echo -n "emails total: "
"${PSQL[@]}" -c "SELECT count(*) FROM ops.emails;" 2>/dev/null || echo "ERR"
echo -n "reviews total: "
"${PSQL[@]}" -c "SELECT count(*) FROM ops.email_reviews;" 2>/dev/null || echo "ERR"
echo -n "emails last 24h: "
"${PSQL[@]}" -c "SELECT count(*) FROM ops.emails WHERE COALESCE(received_at, created_at) > now() - interval '24 hours';" 2>/dev/null || echo "ERR"
echo -n "reviews last 24h: "
"${PSQL[@]}" -c "SELECT count(*) FROM ops.email_reviews WHERE created_at > now() - interval '24 hours';" 2>/dev/null || echo "ERR"
echo "--- latest 8 emails ---"
"${PSQL[@]}" -c "SELECT COALESCE(to_char(COALESCE(received_at, created_at), 'YYYY-MM-DD HH24:MI'), '?') || ' | ' || COALESCE(processing_status,'?') || ' | ' || left(COALESCE(subject,'(no subject)'),60) FROM ops.emails ORDER BY COALESCE(received_at, created_at) DESC NULLS LAST LIMIT 8;" 2>/dev/null || echo "ERR"
echo "--- latest 8 reviews ---"
"${PSQL[@]}" -c "SELECT COALESCE(to_char(created_at, 'YYYY-MM-DD HH24:MI'), '?') || ' | ' || COALESCE(urgency::text,'?') || ' | ' || left(COALESCE(summary, analysis_summary, ''),80) FROM ops.email_reviews ORDER BY created_at DESC NULLS LAST LIMIT 8;" 2>/dev/null || \
"${PSQL[@]}" -c "\d ops.email_reviews" 2>/dev/null || echo "ERR reviews"
echo
echo "=== cron install script expects ==="
grep -E 'CRON|schedule|\*/' /docker/clawsum/scripts/install-gmail-inbox-review-cron.sh 2>/dev/null | head -20
