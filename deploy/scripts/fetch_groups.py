#!/usr/bin/env python3
import json
import re
import urllib.request
from pathlib import Path

env = Path("/docker/clawsum/.env").read_text()
m = re.search(r"^TELEGRAM_BOT_TOKEN=(.+)$", env, re.M)
if not m:
    print("NO_TOKEN")
    raise SystemExit(1)
token = m.group(1).strip()
url = f"https://api.telegram.org/bot{token}/getUpdates?limit=100"
with urllib.request.urlopen(url) as r:
    data = json.load(r)

chats = {}
for u in data.get("result", []):
    msg = u.get("message") or u.get("channel_post") or {}
    c = msg.get("chat") or {}
    if c.get("type") in ("group", "supergroup") and c.get("title"):
        chats[c["id"]] = c["title"]

print(f"updates={len(data.get('result', []))} groups={len(chats)}")
if not chats:
    print("NO_GROUPS_IN_QUEUE")
else:
    for cid, title in sorted(chats.items(), key=lambda x: x[1].lower()):
        print(f"{title}\t{cid}")
