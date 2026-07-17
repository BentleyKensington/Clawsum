#!/usr/bin/env python3
"""Boss: snapshot Paperclip tasks + recent activity (is work processing?)."""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)

STATUSES = ("backlog", "todo", "in_progress", "blocked", "done", "cancelled")


def agent_name_map() -> dict[str, str]:
    agents = api_get(f"companies/{COMPANY_ID}/agents")
    if not isinstance(agents, list):
        return {}
    return {a["id"]: a.get("name", a["id"][:8]) for a in agents if isinstance(a, dict)}


def api_get(path: str) -> object:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} {path}: {e.read().decode()}") from e


def short_issue(i: dict, names: dict[str, str] | None = None) -> str:
    title = (i.get("title") or "?")[:60]
    aid = i.get("assigneeAgentId")
    assignee = (
        i.get("assigneeAgentName")
        or i.get("assignee")
        or (names.get(aid) if names and aid else None)
        or ("unassigned" if not aid else aid[:8])
    )
    updated = i.get("updatedAt") or i.get("createdAt") or ""
    return f"  - [{i.get('status','?')}] {title} → {assignee} ({updated})"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--in-progress-limit", type=int, default=15)
    p.add_argument("--activity-limit", type=int, default=10)
    args = p.parse_args()

    print(f"Paperclip status @ {datetime.now().isoformat(timespec='seconds')}")
    print(f"API: {API}  company: {COMPANY_ID}\n")

    names = agent_name_map()

    # Agents + heartbeats
    agents = api_get(f"companies/{COMPANY_ID}/agents")
    if isinstance(agents, list):
        print("Agents (heartbeat):")
        for a in agents:
            if not isinstance(a, dict):
                continue
            hb = (a.get("runtimeConfig") or {}).get("heartbeat") or {}
            enabled = hb.get("enabled", False)
            interval = hb.get("intervalMs", "?")
            print(
                f"  {a.get('name','?'):22} heartbeat={'ON' if enabled else 'OFF'} "
                f"intervalMs={interval} adapter={a.get('adapterType','?')}"
            )
        print()

    total = 0
    for status in STATUSES:
        issues = api_get(f"companies/{COMPANY_ID}/issues?status={status}")
        if not isinstance(issues, list):
            issues = []
        total += len(issues)
        print(f"{status}: {len(issues)}")
        limit = args.in_progress_limit if status == "in_progress" else 5
        for i in issues[:limit]:
            if isinstance(i, dict):
                print(short_issue(i, names))
        if len(issues) > limit:
            print(f"  … +{len(issues) - limit} more in Boss UI")
        print()

    activity = api_get(f"companies/{COMPANY_ID}/activity")
    if isinstance(activity, list) and activity:
        print(f"Recent activity ({min(len(activity), args.activity_limit)}):")
        for ev in activity[: args.activity_limit]:
            if isinstance(ev, dict):
                kind = ev.get("type") or ev.get("action") or "event"
                msg = ev.get("message") or ev.get("summary") or ev.get("title") or ""
                ts = ev.get("createdAt") or ev.get("timestamp") or ""
                print(f"  - {ts} {kind}: {str(msg)[:80]}")
    else:
        print("Recent activity: (none or API returned empty)")
        print(
            "  If tasks stay in 'todo', check heartbeats ON and gateway healthy (curl :48166/healthz)."
        )

    print(f"\nTotal issues listed across statuses: {total}")
    print("Boss UI: ssh -L 3100:127.0.0.1:3100 clawsum → http://localhost:3100")


if __name__ == "__main__":
    main()
