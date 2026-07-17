#!/usr/bin/env python3
import json, re, urllib.request
from pathlib import Path

token = re.search(r"^TELEGRAM_BOT_TOKEN=(.+)$", Path("/docker/clawsum/.env").read_text(), re.M).group(1).strip()
url = f"https://api.telegram.org/bot{token}/getUpdates?limit=100"
req = urllib.request.Request(url, method="GET")
with urllib.request.urlopen(req, timeout=15) as r:
    data = json.load(r)

chats = {}
for u in data.get("result", []):
    m = u.get("message") or u.get("my_chat_member") or {}
    c = m.get("chat") or {}
    if c.get("type") in ("group", "supergroup") and c.get("title"):
        chats[c["id"]] = c["title"]

print(f"updates={len(data.get('result', []))} groups={len(chats)}")
for cid, title in sorted(chats.items(), key=lambda x: x[1].lower()):
    print(f"{title}\t{cid}")
