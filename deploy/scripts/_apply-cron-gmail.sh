#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
for f in run-at-chicago.sh install-ghl-weekly-report-cron.sh install-content-factory-cron.sh \
         install-platform-crons.sh install-reminders-cron.sh; do
  sed -i 's/\r$//' "/tmp/$f"
  cp -f "/tmp/$f" "$R/scripts/$f"
  chmod +x "$R/scripts/$f"
done
bash "$R/scripts/install-ghl-weekly-report-cron.sh"
bash "$R/scripts/install-content-factory-cron.sh"
# Re-pin backup to Chicago 03:00 via hourly gate
# shellcheck source=/dev/null
source "$R/scripts/lib/ensure-cron-tz.sh"
install_cron_line 'clawsum-platform-cron-backup' \
  "0 * * * * /bin/bash $R/scripts/run-at-chicago.sh 3 0 4 -- /bin/bash $R/scripts/backup-platform.sh >> $R/data/backups/backup.log 2>&1 # clawsum-platform-cron-backup"

echo "=== crontab now ==="
crontab -l
echo "=== content-factory cron.d ==="
cat /etc/cron.d/clawsum-content-factory

# Rotate 128MB OAuth traceback log
LOG=$R/data/reports/gmail-inbox-pipeline.log
if [[ -f "$LOG" ]] && [[ "$(stat -c%s "$LOG")" -gt 5000000 ]]; then
  mv -f "$LOG" "$LOG.old"
  echo rotated_gmail_pipeline_log
fi

echo "=== gmail oauth url ==="
python3 "$R/scripts/gmail-reauth-console.py" --print-url-only
