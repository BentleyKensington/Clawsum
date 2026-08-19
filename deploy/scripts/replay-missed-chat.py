#!/usr/bin/env python3
"""Replay Discord (and optional Telegram) messages missed during a chat outage.

Env:
  SINCE_ISO          ISO start of outage window (required for CLI unless --since)
  DRY_RUN=1          Plan only
  REPLAY_LIMIT=20    Max messages to deliver
  TELEGRAM_REPLAY=1  Also pull Telegram getUpdates (off by default — steals from gateway poll)
  AGENT=admin        OpenClaw agent id
  CLAWSUM_ROOT       Default /docker/clawsum
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
STATE_DIR = ROOT / "data" / "chat-replay"
OUT = Path(os.environ.get("CLAWSUM_REPLAY_OUT", "/tmp/clawsum-replay"))
GATEWAY = os.environ.get("OPENCLAW_GATEWAY_CONTAINER", "clawsum-openclaw-gateway-1")
AGENT = os.environ.get("AGENT", "admin")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def parse_iso(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def discord_api(token: str, path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "ClawsumReplay/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def load_replayed() -> set[str]:
    path = STATE_DIR / "replayed-ids.json"
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("ids") or [])
    except (OSError, json.JSONDecodeError):
        return set()


def save_replayed(ids: set[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Keep newest ~2000 ids
    trimmed = sorted(ids)[-2000:]
    (STATE_DIR / "replayed-ids.json").write_text(
        json.dumps({"ids": trimmed, "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2),
        encoding="utf-8",
    )


def key_for(item: dict) -> str:
    return f"{item['channel']}:{item['target']}:{item['message_id']}"


def collect_discord(token: str, since: datetime, cfg: dict) -> list[dict]:
    discord = (cfg.get("channels") or {}).get("discord") or {}
    guilds = discord.get("guilds") or {}
    channel_meta = []
    for _gid, gcfg in guilds.items():
        for cid, ccfg in (gcfg.get("channels") or {}).items():
            if ccfg.get("enabled") is False:
                continue
            cid_s = str(cid).strip()
            if not cid_s.isdigit():
                continue
            channel_meta.append(
                {
                    "id": cid_s,
                    "requireMention": bool(ccfg.get("requireMention", True)),
                }
            )

    me = discord_api(token, "/users/@me")
    bot_id = str(me.get("id"))
    print(f"discord_bot={me.get('username')} id={bot_id} channels={len(channel_meta)}")

    candidates: list[dict] = []
    for ch in channel_meta:
        cid = ch["id"]
        try:
            msgs = discord_api(token, f"/channels/{cid}/messages?limit=50")
        except Exception as e:
            print(f"channel_fail {cid} {type(e).__name__}")
            continue

        # API returns newest-first; build timeline oldest→newest for reply detection
        chronological = list(reversed(msgs))
        for i, m in enumerate(chronological):
            author = m.get("author") or {}
            if author.get("bot"):
                continue
            ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
            if ts < since:
                continue
            content = (m.get("content") or "").strip()
            if not content:
                continue
            mentioned = any(str(u.get("id")) == bot_id for u in (m.get("mentions") or []))
            if ch["requireMention"] and not mentioned and f"<@{bot_id}>" not in content:
                continue

            # Skip if Clawsum already replied after this message in-channel
            already = False
            for later in chronological[i + 1 :]:
                la = later.get("author") or {}
                if str(la.get("id")) == bot_id or la.get("bot"):
                    already = True
                    break
            if already:
                print(f"skip_answered discord {cid} {m['id']}")
                continue

            candidates.append(
                {
                    "channel": "discord",
                    "target": cid,
                    "message_id": m["id"],
                    "author": author.get("username"),
                    "timestamp": m["timestamp"],
                    "content": content[:1800],
                }
            )
        time.sleep(0.25)
    return candidates


def collect_telegram(token: str, since: datetime) -> list[dict]:
    url = f"https://api.telegram.org/bot{token}/getUpdates?limit=50&timeout=0"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read().decode())
    items: list[dict] = []
    for u in data.get("result") or []:
        msg = u.get("message") or u.get("edited_message") or {}
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        date = datetime.fromtimestamp(msg.get("date", 0), tz=timezone.utc)
        if date < since:
            continue
        chat = msg.get("chat") or {}
        items.append(
            {
                "channel": "telegram",
                "target": str(chat.get("id")),
                "message_id": str(msg.get("message_id")),
                "author": (msg.get("from") or {}).get("username"),
                "timestamp": date.isoformat(),
                "content": text[:1800],
            }
        )
    print(f"telegram_pending_updates={len(items)}")
    return items


def deliver(item: dict) -> dict:
    msg = (
        f"[REPLAY of missed message while Clawsum was offline]\n"
        f"From: {item.get('author')}\n"
        f"When: {item['timestamp']}\n"
        f"Original:\n{item['content']}\n\n"
        f"Please respond helpfully to the original message now."
    )
    cmd = [
        "docker",
        "exec",
        "-u",
        "node",
        GATEWAY,
        "openclaw",
        "agent",
        "--agent",
        AGENT,
        "--channel",
        item["channel"],
        "--message",
        msg,
        "--deliver",
        "--reply-channel",
        item["channel"],
        "--reply-to",
        item["target"],
        "--timeout",
        "180",
    ]
    print(f"REPLAY {item['channel']}->{item['target']} ...")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        ok = proc.returncode == 0
        result = {
            "ok": ok,
            "code": proc.returncode,
            "key": key_for(item),
            "target": item["target"],
            "channel": item["channel"],
            "stdout": (proc.stdout or "")[-500],
            "stderr": (proc.stderr or "")[-500],
        }
        print("  =>", "OK" if ok else f"FAIL {proc.returncode}")
        if not ok:
            print((proc.stderr or proc.stdout or "")[-300])
        return result
    except Exception as e:
        print("  => EXC", e)
        return {"ok": False, "error": str(e), "key": key_for(item), "target": item["target"]}


def run_replay(
    since: datetime,
    *,
    dry_run: bool = False,
    limit: int = 20,
    telegram_replay: bool = False,
) -> dict:
    """Collect and optionally deliver missed messages since `since`. Returns summary dict."""
    OUT.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    env = load_env()
    cfg = json.loads((ROOT / "data/.openclaw/openclaw.json").read_text(encoding="utf-8"))
    replayed = load_replayed()

    candidates: list[dict] = []
    token = env.get("DISCORD_BOT_TOKEN", "")
    if token:
        candidates.extend(collect_discord(token, since, cfg))
    else:
        print("NO_DISCORD_TOKEN")

    tg_token = env.get("TELEGRAM_BOT_TOKEN", "")
    if telegram_replay and tg_token:
        try:
            candidates.extend(collect_telegram(tg_token, since))
        except Exception as e:
            print(f"telegram_getUpdates_fail {type(e).__name__}: {e}")
    elif telegram_replay:
        print("NO_TELEGRAM_TOKEN")
    else:
        print("telegram_replay=skipped (gateway polling owns getUpdates)")

    # Dedupe by message + drop already replayed
    seen: set[str] = set()
    plan: list[dict] = []
    for c in sorted(candidates, key=lambda x: x["timestamp"]):
        k = key_for(c)
        if k in seen or k in replayed:
            if k in replayed:
                print(f"skip_replayed {k}")
            continue
        seen.add(k)
        plan.append(c)
    plan = plan[-limit:]

    (OUT / "replay-plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"plan={len(plan)} dry_run={dry_run} since={since.isoformat()}")
    for p in plan:
        print(
            f"- {p['channel']} {p['target']} {p['timestamp']} "
            f"{p['content'][:70].replace(chr(10), ' ')}"
        )

    summary = {
        "since": since.isoformat(),
        "dry_run": dry_run,
        "planned": len(plan),
        "delivered_ok": 0,
        "delivered_fail": 0,
        "results": [],
    }
    if dry_run or not plan:
        print("STOP dry_run or empty plan")
        return summary

    results = []
    for p in plan:
        r = deliver(p)
        results.append(r)
        if r.get("ok"):
            replayed.add(key_for(p))
            summary["delivered_ok"] += 1
        else:
            summary["delivered_fail"] += 1
        time.sleep(2)

    save_replayed(replayed)
    summary["results"] = results
    (OUT / "replay-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"REPLAY_DONE ok={summary['delivered_ok']}/{len(results)}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay missed Discord/Telegram chat after outage")
    parser.add_argument("--since", default=os.environ.get("SINCE_ISO"), help="ISO timestamp")
    parser.add_argument("--dry-run", action="store_true", default=os.environ.get("DRY_RUN") == "1")
    parser.add_argument("--limit", type=int, default=int(os.environ.get("REPLAY_LIMIT", "20")))
    parser.add_argument(
        "--telegram",
        action="store_true",
        default=os.environ.get("TELEGRAM_REPLAY") == "1",
        help="Also consume Telegram getUpdates (risky while gateway polls)",
    )
    args = parser.parse_args()
    if not args.since:
        print("ERROR: --since or SINCE_ISO required")
        return 2
    summary = run_replay(
        parse_iso(args.since),
        dry_run=args.dry_run,
        limit=args.limit,
        telegram_replay=args.telegram,
    )
    if summary["dry_run"] or summary["planned"] == 0:
        return 0
    return 0 if summary["delivered_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
