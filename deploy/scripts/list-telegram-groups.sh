#!/bin/bash
set -euo pipefail
TELEGRAM_BOT_TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' /docker/clawsum/.env | cut -d= -f2- | tr -d '\r')
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates?limit=100" \
  | python3 <<'PY'
import json, sys
d = json.load(sys.stdin)
chats = {}
for u in d.get("result", []):
    m = u.get("message") or u.get("channel_post") or {}
    c = m.get("chat") or {}
    if c.get("type") in ("group", "supergroup") and c.get("title"):
        chats[c["id"]] = c["title"]
if not chats:
    print("NO_GROUPS_FOUND")
    sys.exit(0)
for cid, title in sorted(chats.items(), key=lambda x: x[1].lower()):
    print(f"{title}\t{cid}")
PY
