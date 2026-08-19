#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

env = {}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    k, _, v = raw.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

token = env["DISCORD_BOT_TOKEN"]
headers = {"Authorization": f"Bot {token}", "User-Agent": "ClawsumHQ/1.0"}

def get(path):
    req = urllib.request.Request("https://discord.com/api/v10" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

app = get("/oauth2/applications/@me")
flags = app.get("flags", 0)
# Discord application flags for privileged intents
# GATEWAY_PRESENCE = 1 << 12 = 4096
# GATEWAY_PRESENCE_LIMITED = 1 << 13 = 8192
# GATEWAY_GUILD_MEMBERS = 1 << 14 = 16384
# GATEWAY_GUILD_MEMBERS_LIMITED = 1 << 15 = 32768
# GATEWAY_MESSAGE_CONTENT = 1 << 18 = 262144
# GATEWAY_MESSAGE_CONTENT_LIMITED = 1 << 19 = 524288
checks = {
    "MESSAGE_CONTENT": 1 << 18,
    "MESSAGE_CONTENT_LIMITED": 1 << 19,
    "GUILD_MEMBERS": 1 << 14,
    "GUILD_MEMBERS_LIMITED": 1 << 15,
    "PRESENCE": 1 << 12,
    "PRESENCE_LIMITED": 1 << 13,
}
print("app", app.get("name"), "flags", flags)
for name, bit in checks.items():
    print(f"  {name}: {bool(flags & bit)}")

gw = get("/gateway/bot")
print("gateway_url", gw.get("url"))
print("session_start_limit", gw.get("session_start_limit"))
print("shards", gw.get("shards"))
