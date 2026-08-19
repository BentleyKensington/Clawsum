#!/usr/bin/env python3
from pathlib import Path
import urllib.request
import urllib.error
import json

env = {}
for line in Path("/docker/clawsum/.env").read_text(encoding="utf-8", errors="replace").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    k, _, v = raw.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

t = env.get("DISCORD_BOT_TOKEN", "")
print("len", len(t))
print("dots", t.count("."))
print("has_space", " " in t)
print("has_Bot_prefix", t.startswith("Bot "))
print("starts", repr(t[:6]) if t else "")
print("chars_ok", all(c.isalnum() or c in "._-" for c in t))

# try auth
req = urllib.request.Request(
    "https://discord.com/api/v10/users/@me",
    headers={"Authorization": f"Bot {t}", "User-Agent": "ClawsumHQ/1.0"},
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        me = json.loads(resp.read().decode())
        print("auth_ok", me.get("username"), me.get("id"), "bot=", me.get("bot"))
except Exception as e:
    print("auth_fail", type(e).__name__, str(e)[:200])
    if hasattr(e, "read"):
        try:
            print("body", e.read().decode()[:300])
        except Exception:
            pass

channel = env.get("DISCORD_ALERT_CHANNEL_ID", "")
guild = env.get("DISCORD_GUILD_ID", "")
if channel:
    try:
        ch_req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{channel}",
            headers={"Authorization": f"Bot {t}", "User-Agent": "ClawsumHQ/1.0"},
        )
        with urllib.request.urlopen(ch_req, timeout=20) as resp:
            ch = json.loads(resp.read().decode())
            print("channel_ok", ch.get("name"), ch.get("type"))
            print("overwrites", len(ch.get("permission_overwrites") or []))
    except Exception as e:
        print("channel_fail", type(e).__name__, str(e)[:200])

if channel:
    msg_req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        data=json.dumps({"content": "Clawsum debug permission probe"}).encode(),
        headers={
            "Authorization": f"Bot {t}",
            "User-Agent": "ClawsumHQ/1.0",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(msg_req, timeout=20) as resp:
            body = json.loads(resp.read().decode())
            print("post_ok", body.get("id"))
    except urllib.error.HTTPError as e:
        print("post_fail", e.code)
        try:
            print("post_body", e.read().decode()[:500])
        except Exception:
            pass
