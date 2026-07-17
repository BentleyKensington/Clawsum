#!/usr/bin/env python3
"""
Pause agent work while Boss answers clarification questions.

Paperclip has NO status named "pending" or "on_hold". Statuses are:
  backlog | todo | in_progress | in_review | blocked | done | cancelled

- `todo` = ready for agents (heartbeats WILL pick these up)
- `backlog` = not started (better semantics, but heartbeats can still checkout)

To actually stop runs you MUST also disable heartbeats:
  python3 disable-paperclip-heartbeats.py

This script moves issues to `backlog` and posts a hold comment.
"""
from __future__ import annotations

import json
import urllib.request

API = "http://127.0.0.1:3100/api"
COMPANY = ""
MARKER = "<!-- clawsum-analyzed:"
HOLD_NOTE = (
    "**On hold — waiting for Boss**\n\n"
    "Status set to **backlog** until you reply to the clarification questions above "
    "(or say *approved as written*).\n\n"
    "Agents will not start new work while heartbeats are OFF. "
    "After you reply, ops will move approved tasks to **todo** / **in_progress** "
    "and re-enable heartbeats."
)


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
        return resp.status, json.loads(raw) if raw else None


def main() -> None:
    code, issues = api("GET", f"companies/{COMPANY}/issues?limit=500")
    if code != 200:
        raise SystemExit(code)
    n = 0
    for i in issues:
        if MARKER not in (i.get("description") or ""):
            continue
        if "Boss clarifications —" in (i.get("title") or ""):
            continue
        st = i.get("status")
        if st in ("done", "cancelled"):
            continue
        if st == "backlog" and HOLD_NOTE.split("\n")[0] in str(i.get("description") or ""):
            continue
        api(
            "PATCH",
            f"issues/{i['id']}",
            {"status": "backlog", "comment": HOLD_NOTE},
        )
        n += 1
        print(f"  backlog {i.get('identifier')}: {(i.get('title') or '')[:50]}")
    print(f"Set {n} issues to backlog (waiting on Boss).")
    print("Ensure heartbeats are OFF: python3 disable-paperclip-heartbeats.py")


if __name__ == "__main__":
    main()
