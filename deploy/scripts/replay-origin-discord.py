#!/usr/bin/env python3
"""Find unanswered Discord 'Origin' message and deliver via openclaw (no restarts)."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/docker/clawsum")
SINCE = datetime.fromisoformat("2026-08-06T04:00:00+00:00")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def discord_api(token: str, path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "ClawsumReplay/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main() -> int:
    env = load_env()
    token = env["DISCORD_BOT_TOKEN"]
    cfg = json.loads((ROOT / "data/.openclaw/openclaw.json").read_text())
    me = discord_api(token, "/users/@me")
    bot_id = str(me["id"])
    guilds = ((cfg.get("channels") or {}).get("discord") or {}).get("guilds") or {}
    targets = []
    for _g, gcfg in guilds.items():
        for cid, ccfg in (gcfg.get("channels") or {}).items():
            cid_s = str(cid).strip()
            if not cid_s.isdigit():
                continue
            if ccfg.get("enabled") is False:
                continue
            try:
                msgs = discord_api(token, f"/channels/{cid_s}/messages?limit=40")
            except Exception as e:
                print("fail", cid_s, type(e).__name__)
                continue
            chrono = list(reversed(msgs))
            for i, m in enumerate(chrono):
                a = m.get("author") or {}
                if a.get("bot"):
                    continue
                ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
                if ts < SINCE:
                    continue
                content = (m.get("content") or "").strip()
                if not content:
                    continue
                # unanswered: no later bot msg
                answered = any(
                    (later.get("author") or {}).get("bot") or str((later.get("author") or {}).get("id")) == bot_id
                    for later in chrono[i + 1 :]
                )
                if answered:
                    continue
                if "origin" in content.lower() or True:
                    # collect all unanswered since SINCE; prefer Origin
                    targets.append(
                        {
                            "cid": cid_s,
                            "id": m["id"],
                            "ts": m["timestamp"],
                            "author": a.get("username"),
                            "content": content[:1800],
                            "origin": "origin" in content.lower(),
                        }
                    )
            time.sleep(0.2)

    # Prefer Origin messages; else all unanswered (cap 5)
    plan = [t for t in targets if t["origin"]] or targets
    plan = plan[:5]
    print(f"unanswered={len(targets)} plan={len(plan)}")
    for p in plan:
        print(p["ts"], p["cid"], p["content"][:80].replace("\n", " "))

    for p in plan:
        msg = (
            f"[REPLAY / follow-up — message had no bot reply]\n"
            f"From: {p['author']}\nWhen: {p['ts']}\nOriginal:\n{p['content']}\n\n"
            "Please respond helpfully now. If this is about Origin as a standalone agent, "
            "break down the request and propose Paperclip tasks / agent wiring."
        )
        cmd = [
            "docker",
            "exec",
            "-u",
            "node",
            "clawsum-openclaw-gateway-1",
            "openclaw",
            "agent",
            "--agent",
            "admin",
            "--channel",
            "discord",
            "--message",
            msg,
            "--deliver",
            "--reply-channel",
            "discord",
            "--reply-to",
            p["cid"],
            "--timeout",
            "180",
        ]
        print("REPLAY", p["cid"], "...")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        print(" =>", "OK" if proc.returncode == 0 else f"FAIL {proc.returncode}")
        if proc.returncode != 0:
            print((proc.stderr or proc.stdout or "")[-400])
        time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
