#!/usr/bin/env bash
# Install cron: sync clawsums@gmail.com then review/analyze every email for Hermes.
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

WRAPPER="/docker/clawsum/scripts/run-gmail-inbox-pipeline.sh"
LOG="/docker/clawsum/data/reports/gmail-inbox-pipeline.log"
mkdir -p /docker/clawsum/data/reports /docker/clawsum/data/inbox-reports

# Ensure pipeline script is present and executable
if [[ "${SCRIPT_DIR}/run-gmail-inbox-pipeline.sh" != "$WRAPPER" ]]; then
  install -m 0755 "${SCRIPT_DIR}/run-gmail-inbox-pipeline.sh" "$WRAPPER"
else
  chmod +x "$WRAPPER"
fi

existing="$(crontab -l 2>/dev/null || true)"
{
  echo "CRON_TZ=America/Chicago"
  echo "${existing}" \
    | grep -v '^CRON_TZ=' \
    | grep -v 'gmail-sync.py' \
    | grep -v 'run-gmail-inbox-pipeline.sh' \
    | grep -v 'gmail-inbox-review.py' \
    || true
  echo "*/15 * * * * /bin/bash ${WRAPPER} >> ${LOG} 2>&1"
} | crontab -

echo "Installed Gmail inbox pipeline cron (sync + review every 15m, CRON_TZ=America/Chicago):"
crontab -l | grep -E 'CRON_TZ|gmail|inbox' || true
echo ""
echo "Run once now:"
echo "  bash ${WRAPPER}"
