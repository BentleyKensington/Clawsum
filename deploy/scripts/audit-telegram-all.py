#!/usr/bin/env python3
"""Full Telegram + agent health audit for Clawsum."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

ROOT = Path("/docker/clawsum/data/.openclaw")
CONFIG = ROOT / "openclaw.json"
AGENTS = ghl.all_clawsum_openclaw_agent_ids()


def chicago_dates():
    now = datetime.now(ZoneInfo("America/Chicago"))
    today = now.strftime("%Y-%m-%d")
    from datetime import timedelta

    yday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return today, yday


def match_agent(title: str):
    return ghl.match_telegram_agent(title)


def load_config():
    return json.loads(CONFIG.read_text())


def list_bindings(cfg):
    bindings = cfg.get("bindings") or []
    if not isinstance(bindings, list):
        return []
    out = []
    for b in bindings:
        if not isinstance(b, dict):
            continue
        peer = (b.get("match") or {}).get("peer") or {}
        if (b.get("match") or {}).get("channel") == "telegram" and peer.get("kind") == "group":
            out.append(
                {
                    "agentId": b.get("agentId"),
                    "groupId": str(peer.get("id")),
                }
            )
    return out


def collect_session_groups():
    groups = {}
    for sessions_file in (ROOT / "agents").glob("*/sessions/sessions.json"):
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


def telegram_channel(cfg):
    ch = cfg.get("channels")
    if isinstance(ch, dict):
        return ch.get("telegram") or {}
    return {}


def agent_status(agent_id: str, today: str, yday: str):
    ws = ROOT / f"workspace-{agent_id}"
    mem_ok = all((ws / "memory" / d).exists() for d in (today, yday))
    auth_path = ROOT / "agents" / agent_id / "agent" / "auth-profiles.json"
    auth = {}
    if auth_path.exists():
        profs = json.loads(auth_path.read_text()).get("profiles") or {}
        auth = {
            "codex": any("openai-codex" in k for k in profs),
            "api_key": "openai:default" in profs,
        }
    sess_dir = ROOT / "agents" / agent_id / "sessions"
    errors = []
    latest = None
    if sess_dir.exists():
        files = sorted(
            [p for p in sess_dir.glob("*.jsonl") if "trajectory" not in p.name],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if files:
            latest = files[0].name
            text = files[0].read_text(errors="replace")[-8000:]
            for needle in (
                "isError\":true",
                "went wrong",
                "api.key",
                "Missing",
                "ENOENT",
                "rate limit",
                "auth",
            ):
                if needle.lower() in text.lower():
                    errors.append(needle)
    return {
        "memory": mem_ok,
        "auth": auth,
        "latest_session": latest,
        "session_flags": errors,
    }


def main():
    today, yday = chicago_dates()
    cfg = load_config()
    tg = telegram_channel(cfg)
    print(f"Chicago dates: today={today} yesterday={yday}")
    print(f"Telegram enabled: {tg.get('enabled')}")
    print(f"groupPolicy: {tg.get('groupPolicy')}")
    print(f"requireMention: {tg.get('requireMention', tg.get('groups', {}).get('*', {}).get('requireMention'))}")

    bindings = list_bindings(cfg)
    print(f"\n=== Bindings in openclaw.json ({len(bindings)}) ===")
    by_agent = {}
    for b in bindings:
        by_agent.setdefault(b["agentId"], []).append(b["groupId"])
        print(f"  {b['agentId']:12} <- group {b['groupId']}")

    session_groups = collect_session_groups()
    print(f"\n=== Groups seen in session store ({len(session_groups)}) ===")
    for gid, title in sorted(session_groups.items(), key=lambda x: (x[1] or "").lower()):
        expected = match_agent(title)
        bound = [b["agentId"] for b in bindings if b["groupId"] == gid]
        status = "OK" if bound and expected in bound else ("UNBOUND" if not bound else f"MISMATCH bound={bound} expected={expected}")
        print(f"  [{status}] {title!r} id={gid} -> {expected}")

    print("\n=== Per-agent health ===")
    for aid in AGENTS:
        st = agent_status(aid, today, yday)
        flags = ",".join(st["session_flags"]) if st["session_flags"] else "clean"
        print(
            f"  {aid:12} mem={st['memory']} codex={st['auth'].get('codex')} "
            f"api_key={st['auth'].get('api_key')} session={st['latest_session'] or 'none'} flags={flags}"
        )

    bound_agents = set(by_agent)
    missing_binding = [a for a in AGENTS if a not in bound_agents and a != "admin"]
    if missing_binding:
        print(f"\nWARN: agents with no group binding: {missing_binding}")

    unbound_groups = [
        gid
        for gid, title in session_groups.items()
        if not any(b["groupId"] == gid for b in bindings)
    ]
    if unbound_groups:
        print(f"\nWARN: groups in sessions but not in bindings: {len(unbound_groups)}")
        for gid in unbound_groups:
            print(f"  {session_groups[gid]} ({gid})")


if __name__ == "__main__":
    main()
