#!/usr/bin/env bash
set -eu
echo "=== date ==="
date
echo "=== chicago ==="
TZ=America/Chicago date
echo "=== utc ==="
date -u
echo "=== crontab ==="
crontab -l 2>/dev/null || echo NO_ROOT_CRONTAB
echo "=== cron.d clawsum ==="
ls -la /etc/cron.d/clawsum* 2>/dev/null || true
grep -h . /etc/cron.d/clawsum* 2>/dev/null || true
echo "=== recent cron log ==="
grep -E 'CRON|daily|ghl|report|brief|gmail' /var/log/syslog 2>/dev/null | tail -40 || journalctl -u cron --since '2 hours ago' --no-pager 2>/dev/null | tail -40 || true
echo "=== report files tonight ==="
ls -lt /docker/clawsum/data/reports/*.md /docker/clawsum/data/reports/*.log 2>/dev/null | head -20
echo "=== ghl weekly dir ==="
ls -lt /docker/clawsum/data/reports/ghl-weekly 2>/dev/null | head -15
echo "=== brief marker ==="
ls -la /docker/clawsum/data/reports/.brief-sent-* 2>/dev/null || true
tail -20 /docker/clawsum/data/reports/cron.log 2>/dev/null || true
echo "=== gmail health json ==="
cat /docker/clawsum/data/reports/gmail-oauth-health.json 2>/dev/null || echo none
echo "=== gmail health run ==="
python3 /docker/clawsum/scripts/gmail_oauth_health.py --dry-run 2>&1 | head -40
echo "=== gmail sync last ==="
tail -30 /docker/clawsum/data/reports/gmail-sync.log 2>/dev/null || tail -30 /docker/clawsum/data/reports/gmail-inbox.log 2>/dev/null || true
