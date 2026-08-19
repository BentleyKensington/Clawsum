#!/usr/bin/env python3
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path("/docker/clawsum")
env = {}
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

token = env["DISCORD_BOT_TOKEN"]
cid = "1534110164427214949"
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{cid}/messages?limit=15",
    headers={"Authorization": f"Bot {token}", "User-Agent": "ClawsumReplay/1.0"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    msgs = json.loads(r.read().decode())
print("=== discord channel recent ===")
for m in reversed(msgs):
    a = m.get("author") or {}
    print(
        m["timestamp"],
        "bot=" + str(bool(a.get("bot"))),
        "@" + str(a.get("username")),
        "|",
        (m.get("content") or "")[:180].replace("\n", " "),
    )

print("=== telegram webhook/updates ===")
tg = env.get("TELEGRAM_BOT_TOKEN", "")
if tg:
    with urllib.request.urlopen(
        f"https://api.telegram.org/bot{tg}/getWebhookInfo", timeout=20
    ) as r:
        print(r.read().decode()[:500])
    with urllib.request.urlopen(
        f"https://api.telegram.org/bot{tg}/getUpdates?limit=5&offset=-5", timeout=20
    ) as r:
        data = json.loads(r.read().decode())
    print("updates", len(data.get("result") or []))
    for u in data.get("result") or []:
        print(json.dumps(u)[:350])

print("=== gateway log hits ===")
proc = subprocess.run(
    [
        "docker",
        "logs",
        "clawsum-openclaw-gateway-1",
        "--since",
        "2026-08-05T02:00:00",
    ],
    capture_output=True,
    text=True,
)
lines = (proc.stdout or "") + "\n" + (proc.stderr or "")
keys = ("telegram", "discord", "inbound", "Status", "mention", "deliver")
hits = [ln for ln in lines.splitlines() if any(k.lower() in ln.lower() for k in keys)]
for ln in hits[-80:]:
    print(ln[:300])
