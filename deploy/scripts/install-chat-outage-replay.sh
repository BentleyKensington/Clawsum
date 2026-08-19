#!/usr/bin/env bash
# Install minute cron: detect Discord/Telegram/gateway outages and replay on recovery.
set -eu
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
WATCH="${ROOT}/scripts/chat-outage-watch.py"
REPLAY="${ROOT}/scripts/replay-missed-chat.py"
CRON_FILE=/etc/cron.d/clawsum-chat-outage-replay

mkdir -p "${ROOT}/data/chat-replay" /var/log
chmod +x "$WATCH" "$REPLAY" 2>/dev/null || true

# Seed state as healthy if missing so we don't replay the entire lookback on first install
if [[ ! -f "${ROOT}/data/chat-replay/outage-state.json" ]]; then
  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
p = Path("${ROOT}/data/chat-replay/outage-state.json")
p.parent.mkdir(parents=True, exist_ok=True)
now = datetime.now(timezone.utc).isoformat()
p.write_text(json.dumps({
    "healthy": True,
    "outage_started_at": None,
    "outage_reasons": [],
    "last_healthy_at": now,
    "last_replay_at": None,
    "last_replay_since": None,
    "last_replay_ok": 0,
    "last_replay_planned": 0,
    "events": [{"at": now, "kind": "watch_installed"}],
}, indent=2))
print("seeded", p)
PY
fi

cat >"$CRON_FILE" <<EOF
# Clawsum: auto-replay Discord messages after chat/gateway outages
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
* * * * * root /usr/bin/python3 ${ROOT}/scripts/chat-outage-watch.py >>/var/log/clawsum-chat-outage-watch.log 2>&1
EOF
chmod 0644 "$CRON_FILE"

echo "Installed $CRON_FILE"
echo "Manual probe:"
python3 "$WATCH" | tee /dev/stderr | tail -20
echo "Log: /var/log/clawsum-chat-outage-watch.log"
echo "State: ${ROOT}/data/chat-replay/outage-state.json"
