#!/usr/bin/env python3
"""
Full pause: heartbeats OFF, agents paused, cancel running heartbeat runs,
backlog all open issues (Boss queue frozen until Boss updates each task).

Usage:
  python3 paperclip-pause-all-work.py
  python3 paperclip-pause-all-work.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:3100/api"
COMPANY = ""

HOLD = (
    "**Parked — waiting for Boss**\n\n"
    "All agent automation is paused. Reply to clarification questions on this issue "
    "(or comment *approved as written*). Ops will move to todo when you are ready."
)

OPEN_STATUSES = ("todo", "in_progress", "blocked", "in_review")
RUNNING = ("running", "queued", "scheduled_retry")


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"error": raw}
        except json.JSONDecodeError:
            return e.code, {"error": raw}


def disable_heartbeats(dry_run: bool) -> None:
    code, agents = api("GET", f"companies/{COMPANY}/agents")
    if code != 200:
        print(f"GET agents failed: {code}", file=sys.stderr)
        return
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        aid = agent["id"]
        name = agent.get("name", aid)
        runtime = agent.get("runtimeConfig") or {}
        hb = runtime.get("heartbeat") or {}
        body = {
            "runtimeConfig": {
                **runtime,
                "heartbeat": {**hb, "enabled": False},
            },
            "status": "paused",
        }
        if dry_run:
            print(f"  [dry-run] heartbeat OFF + paused: {name}")
            continue
        code, _ = api("PATCH", f"agents/{aid}", body)
        print(f"  {name}: heartbeat OFF, status=paused ({code})")


def cancel_active_runs(dry_run: bool) -> None:
    code, runs = api("GET", f"companies/{COMPANY}/heartbeat-runs?limit=200")
    if code != 200 or not isinstance(runs, list):
        print(f"GET heartbeat-runs failed: {code}", file=sys.stderr)
        return
    n = 0
    for run in runs:
        if run.get("status") not in RUNNING:
            continue
        rid = run["id"]
        agent = (run.get("agentId") or "")[:8]
        if dry_run:
            print(f"  [dry-run] cancel run {rid[:8]} ({run.get('status')}) agent={agent}")
        else:
            c, res = api("POST", f"heartbeat-runs/{rid}/cancel", {})
            print(f"  cancel {rid[:8]}: {c}")
            if c not in (200, 201, 204):
                print(f"    {res}", file=sys.stderr)
        n += 1
    print(f"Cancelled or found {n} active heartbeat run(s).")


def backlog_all_issues(dry_run: bool) -> None:
    code, issues = api("GET", f"companies/{COMPANY}/issues?limit=500")
    if code != 200:
        raise SystemExit(f"GET issues failed: {code}")
    n = 0
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        st = issue.get("status")
        if st not in OPEN_STATUSES:
            continue
        ident = issue.get("identifier") or issue["id"][:8]
        title = (issue.get("title") or "")[:55]
        if dry_run:
            print(f"  [dry-run] backlog {ident}: {title}")
            n += 1
            continue
        patch: dict = {
            "status": "backlog",
            "comment": HOLD,
            "assigneeAgentId": None,
        }
        code, res = api("PATCH", f"issues/{issue['id']}", patch)
        if code == 200:
            n += 1
            print(f"  backlog {ident}: {title}")
        else:
            # Retry without clearing assignee if API rejects null
            code2, _ = api(
                "PATCH",
                f"issues/{issue['id']}",
                {"status": "backlog", "comment": HOLD},
            )
            if code2 == 200:
                n += 1
                print(f"  backlog {ident} (kept assignee): {title}")
            else:
                print(f"  FAIL {ident}: {code} {res}", file=sys.stderr)
    print(f"Moved {n} issue(s) to backlog (unassigned where allowed).")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print("=== 1. Disable heartbeats + pause agents ===")
    disable_heartbeats(args.dry_run)

    print("\n=== 2. Cancel running/queued heartbeat runs ===")
    cancel_active_runs(args.dry_run)

    print("\n=== 3. Backlog all open issues ===")
    backlog_all_issues(args.dry_run)

    print("\nDone. Boss UI should stop new Admin runs within ~1 min.")
    print("Resume later: unpause agents, enable-paperclip-heartbeats.py, move tasks to todo.")


if __name__ == "__main__":
    main()
