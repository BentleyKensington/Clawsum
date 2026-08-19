#!/usr/bin/env bash
# Sunday 16:00 America/Chicago LLM Lab watch.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
install -d /etc/cron.d
cat >/etc/cron.d/clawsum-llm-research-watch <<EOF
CRON_TZ=America/Chicago
0 16 * * 0 root cd $ROOT && /usr/bin/python3 $ROOT/scripts/llm-research-watch.py --now >> /var/log/clawsum-llm-research-watch.log 2>&1
EOF
chmod 644 /etc/cron.d/clawsum-llm-research-watch
echo "installed /etc/cron.d/clawsum-llm-research-watch"
