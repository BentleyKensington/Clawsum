#!/usr/bin/env bash
# Content factory at 07:10 / 07:20 America/Chicago (not 07:10 UTC).
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
FILE=/etc/cron.d/clawsum-content-factory
chmod +x "$ROOT/scripts/run-at-chicago.sh" 2>/dev/null || true
cat > "$FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
10 * * * * root $ROOT/scripts/run-at-chicago.sh 7 10 4 -- /usr/bin/python3 $ROOT/scripts/content-factory.py daily --count 1 >>$ROOT/data/reports/content-factory.log 2>&1
20 * * * * root $ROOT/scripts/run-at-chicago.sh 7 20 4 -- /usr/bin/python3 $ROOT/scripts/content-factory.py run-one >>$ROOT/data/reports/content-factory.log 2>&1
EOF
chmod 644 "$FILE"
echo "installed $FILE (07:10/07:20 America/Chicago)"
