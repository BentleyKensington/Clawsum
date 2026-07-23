#!/usr/bin/env bash
# Ensure crontab schedules use America/Chicago (handles CST/CDT).
# Without CRON_TZ, Vixie/cron on UTC VPS fires "0 7" at 07:00 UTC = 02:00 CDT.
#
# Usage (from install-*-cron.sh):
#   source "$(dirname "$0")/lib/ensure-cron-tz.sh"
#   install_cron_line 'daily-global-report.py' '0 7 * * * /usr/bin/python3 /docker/clawsum/scripts/daily-global-report.py >> ... 2>&1'

ensure_cron_tz() {
  local tz="${CRON_TZ_ZONE:-America/Chicago}"
  local existing
  existing="$(crontab -l 2>/dev/null || true)"
  {
    echo "CRON_TZ=${tz}"
    echo "${existing}" | grep -v '^CRON_TZ=' || true
  } | crontab -
}

# Replace any crontab lines matching needle with new_line; keep single CRON_TZ.
install_cron_line() {
  local needle="$1"
  local new_line="$2"
  local tz="${CRON_TZ_ZONE:-America/Chicago}"
  local existing
  existing="$(crontab -l 2>/dev/null || true)"
  {
    echo "CRON_TZ=${tz}"
    echo "${existing}" | grep -v '^CRON_TZ=' | grep -v "${needle}" || true
    echo "${new_line}"
  } | crontab -
}
