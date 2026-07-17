#!/usr/bin/env python3
"""Bind GHL account agents to Telegram groups (explicit ID + title needles).

Usage:
  python3 bind-ghl-telegram.py --slug ghl
  python3 bind-ghl-telegram.py --slug ghl --group-id <telegram_group_id>
  python3 bind-ghl-telegram.py --all --from-sessions
  python3 bind-ghl-telegram.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
ENV = Path("/docker/clawsum/.env")
AGENTS = Path("/docker/clawsum/data/.openclaw/agents")


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    CONFIG.chmod(0o600)


def env_group_id(account: dict) -> str | None:
    slug = account["slug"].upper().replace("-", "_")
    key = f"GHL_{slug}_TELEGRAM_GROUP_ID"
    val = os.environ.get(key)
    if val:
        return val.strip()
    if ENV.exists():
        m = re.search(rf"^{re.escape(key)}=(.+)$", ENV.read_text(), re.M)
        if m:
            return m.group(1).strip()
    return (account.get("telegram_group_id") or "").strip() or None


def binding_key(agent_id: str, group_id: str) -> tuple[str, str]:
    return agent_id, str(group_id)


def upsert_binding(cfg: dict, agent_id: str, group_id: str) -> bool:
    bindings = list(cfg.get("bindings") or [])
    gid = str(group_id)
    for b in bindings:
        peer = (b.get("match") or {}).get("peer") or {}
        if b.get("agentId") == agent_id and str(peer.get("id")) == gid:
            return False
    # Remove other agents bound to same group (one group -> one agent)
    bindings = [
        b
        for b in bindings
        if str(((b.get("match") or {}).get("peer") or {}).get("id")) != gid
    ]
    bindings.append(
        {
            "agentId": agent_id,
            "match": {"channel": "telegram", "peer": {"kind": "group", "id": gid}},
        }
    )
    cfg["bindings"] = bindings
    cfg.setdefault("channels", {}).setdefault("telegram", {})["enabled"] = True
    cfg.setdefault("plugins", {}).setdefault("entries", {})["telegram"] = {"enabled": True}
    return True


def collect_session_groups() -> dict[str, str]:
    groups: dict[str, str] = {}
    for sessions_file in AGENTS.glob("*/sessions/sessions.json"):
        try:
            data = json.loads(sessions_file.read_text())
        except Exception:
            continue
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            gid = entry.get("groupId")
            subject = entry.get("subject") or (entry.get("origin") or {}).get("label", "")
            if gid and ("group" in key or entry.get("chatType") == "group"):
                groups[str(gid)] = subject or groups.get(str(gid), "")
    return groups


def fetch_telegram_groups() -> dict[str, str]:
    if not ENV.exists():
        return {}
    m = re.search(r"^TELEGRAM_BOT_TOKEN=(.+)$", ENV.read_text(), re.M)
    if not m:
        return {}
    token = m.group(1).strip()
    url = f"https://api.telegram.org/bot{token}/getUpdates?limit=100"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    chats: dict[str, str] = {}
    for u in data.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        c = msg.get("chat") or {}
        if c.get("type") in ("group", "supergroup") and c.get("title"):
            chats[str(c["id"])] = c["title"]
    return chats


def status() -> None:
    cfg = load_config()
    bindings = cfg.get("bindings") or []
    session_groups = collect_session_groups()
    tg_groups = fetch_telegram_groups()
    all_groups = {**session_groups, **tg_groups}

    print("=== GHL Telegram binding status ===\n")
    for acc in ghl.accounts():
        agent = acc["id"]
        explicit = env_group_id(acc)
        bound = [
            str(((b.get("match") or {}).get("peer") or {}).get("id"))
            for b in bindings
            if b.get("agentId") == agent
        ]
        print(f"{acc['display_name']} ({agent})")
        print(f"  needles: {', '.join(acc.get('telegram_needles', []))}")
        print(f"  configured group id: {explicit or '(none)'}")
        print(f"  bound groups: {bound or '(none)'}")
        for gid, title in sorted(all_groups.items(), key=lambda x: x[1].lower()):
            match = ghl.match_telegram_agent(title)
            if match == agent:
                mark = "BOUND" if gid in bound else "MATCH (unbound)"
                print(f"  [{mark}] {title} ({gid})")
        print()


def bind_account(account: dict, group_id: str | None, from_sessions: bool) -> int:
    cfg = load_config()
    added = 0
    agent_id = account["id"]

    targets: list[tuple[str, str]] = []
    gid = group_id or env_group_id(account)
    if gid:
        targets.append((gid, "(explicit)"))

    if from_sessions:
        for sg_id, title in collect_session_groups().items():
            if ghl.match_telegram_agent(title) == agent_id:
                targets.append((sg_id, title))

    for tg_id, title in fetch_telegram_groups().items():
        if ghl.match_telegram_agent(title) == agent_id and (tg_id, title) not in [(t[0], t[1]) for t in targets]:
            targets.append((tg_id, title))

    if not targets:
        print(f"  no group found for {agent_id} — create/rename group or pass --group-id")
        return 0

    seen: set[str] = set()
    for tg_id, title in targets:
        if tg_id in seen:
            continue
        seen.add(tg_id)
        if upsert_binding(cfg, agent_id, tg_id):
            added += 1
            print(f"  bound {agent_id} <- {title} ({tg_id})")
        else:
            print(f"  already bound {agent_id} <- {title} ({tg_id})")

    if added:
        save_config(cfg)
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description="Bind GHL agents to Telegram groups")
    parser.add_argument("--slug", help="Account slug e.g. ghl")
    parser.add_argument("--group-id", help="Telegram group id (overrides config/env)")
    parser.add_argument("--all", action="store_true", help="All GHL accounts with configured group ids")
    parser.add_argument("--from-sessions", action="store_true", help="Also match session store group titles")
    parser.add_argument("--status", action="store_true", help="Show binding status only")
    args = parser.parse_args()

    if args.status:
        status()
        return

    if args.all:
        total = 0
        for acc in ghl.accounts():
            print(f"Binding {acc['id']}...")
            total += bind_account(acc, None, args.from_sessions)
        print(f"\nDone. {total} new binding(s). Restart: docker compose restart openclaw-gateway")
        return

    if not args.slug:
        raise SystemExit("Provide --slug, --all, or --status")

    account = ghl.account_by_slug(args.slug)
    if not account:
        raise SystemExit(f"Unknown slug: {args.slug}")

    print(f"Binding {account['id']} ({account['display_name']})...")
    added = bind_account(account, args.group_id, True)
    print(f"\nDone. {added} new binding(s).")
    if added:
        print("Restart gateway: cd /docker/clawsum && docker compose restart openclaw-gateway")


if __name__ == "__main__":
    main()
