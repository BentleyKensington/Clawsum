#!/usr/bin/env python3
"""Check DMs + whether Status was ingested; list recent telegram sessions."""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
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


def api(path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "ClawsumReplay/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


me = api("/users/@me")
print("me", me.get("username"), me.get("id"))

# Private channels (DMs)
try:
    chans = api("/users/@me/channels")
    print("dm_channels", len(chans))
    since = datetime.fromisoformat("2026-08-05T02:00:00+00:00")
    for ch in chans[:20]:
        cid = ch["id"]
        try:
            msgs = api(f"/channels/{cid}/messages?limit=20")
        except Exception as e:
            print("dm_fail", cid, e)
            continue
        for m in msgs:
            a = m.get("author") or {}
            if a.get("bot"):
                continue
            ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
            if ts < since:
                continue
            print(
                "DM",
                m["timestamp"],
                cid,
                "@" + str(a.get("username")),
                "|",
                (m.get("content") or "")[:160].replace("\n", " "),
            )
except Exception as e:
    print("dm_list_fail", type(e).__name__, e)

# Gateway may have session transcripts
spool = ROOT / "data/.openclaw"
print("=== recent telegram/discord session dirs ===")
for p in sorted(spool.rglob("*"), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)[:80]:
    name = str(p.relative_to(spool))
    if any(k in name.lower() for k in ("telegram", "discord", "ingress", "session")):
        if p.is_file() and p.stat().st_size < 5_000_000:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if mtime >= since:
                print(f"{mtime.isoformat()} {name} size={p.stat().st_size}")
