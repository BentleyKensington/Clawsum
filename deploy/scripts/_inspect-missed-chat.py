#!/usr/bin/env python3
"""Inspect Discord messages since outage window (no replay)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path("/docker/clawsum")
SINCE = datetime.fromisoformat("2026-08-05T02:00:00+00:00")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def api(token: str, path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "ClawsumReplay/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main() -> None:
    env = load_env()
    token = env["DISCORD_BOT_TOKEN"]
    cfg = json.loads((ROOT / "data/.openclaw/openclaw.json").read_text())
    guilds = ((cfg.get("channels") or {}).get("discord") or {}).get("guilds") or {}
    me = api(token, "/users/@me")
    bot_id = str(me["id"])
    print(f"bot={me.get('username')} id={bot_id}")

    fails = []
    all_msgs = []
    for _gid, gcfg in guilds.items():
        for cid, ccfg in (gcfg.get("channels") or {}).items():
            enabled = ccfg.get("enabled") is not False
            req_m = bool(ccfg.get("requireMention", True))
            try:
                msgs = api(token, f"/channels/{cid}/messages?limit=40")
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:180]
                fails.append({"cid": cid, "code": e.code, "body": body, "enabled": enabled})
                continue
            except Exception as e:
                fails.append({"cid": cid, "err": f"{type(e).__name__}: {e}", "enabled": enabled})
                continue
            for m in msgs:
                author = m.get("author") or {}
                if author.get("bot"):
                    continue
                ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
                if ts < SINCE:
                    continue
                content = (m.get("content") or "").strip()
                if not content:
                    continue
                mentioned = any(str(u.get("id")) == bot_id for u in (m.get("mentions") or [])) or (
                    f"<@{bot_id}>" in content
                )
                all_msgs.append(
                    {
                        "cid": str(cid),
                        "ts": m["timestamp"],
                        "author": author.get("username"),
                        "reqMention": req_m,
                        "mentioned": mentioned,
                        "enabled": enabled,
                        "content": content[:240].replace("\n", " "),
                    }
                )

    print(f"fails={len(fails)} msgs_since={len(all_msgs)}")
    for f in fails[:20]:
        print("FAIL", json.dumps(f))
    for m in sorted(all_msgs, key=lambda x: x["ts"]):
        print(
            f"{m['ts']} ch={m['cid']} @{m['author']} "
            f"ment={m['mentioned']} req={m['reqMention']} en={m['enabled']} | {m['content']}"
        )


if __name__ == "__main__":
    main()
