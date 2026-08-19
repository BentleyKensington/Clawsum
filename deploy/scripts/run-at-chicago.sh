#!/usr/bin/env bash
# Run a command only inside an America/Chicago clock window.
# Ubuntu cron on this VPS ignores CRON_TZ, so wall-clock hours are UTC.
#
# Usage: run-at-chicago.sh HOUR MINUTE [SLACK_MIN] -- command...
# Cron should fire every hour at MINUTE. Script no-ops except at HOUR:MINUTE Chicago.
set -euo pipefail
export TZ=America/Chicago
if [[ $# -lt 4 ]]; then
  echo "usage: $0 HOUR MINUTE [SLACK] -- command" >&2
  exit 2
fi
H_WANT="$1"
M_WANT="$2"
shift 2
SLACK=4
if [[ "${1:-}" != "--" ]]; then
  SLACK="$1"
  shift
fi
if [[ "${1:-}" == "--" ]]; then
  shift
fi
H=$(date +%-H)
M=$(date +%-M)
if [ "$H" -ne "$H_WANT" ]; then
  exit 0
fi
if [ "$M" -lt "$M_WANT" ] || [ "$M" -gt $((M_WANT + SLACK)) ]; then
  exit 0
fi
exec "$@"
