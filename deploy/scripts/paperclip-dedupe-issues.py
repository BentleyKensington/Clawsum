#!/usr/bin/env python3
"""Cancel duplicate / noise Paperclip issues (productivity reviews, re-delegated CLA-3x)."""
from __future__ import annotations

import json
import re
import urllib.request

API = "http://127.0.0.1:3100/api"
COMPANY = ""

PRODUCTIVITY_PREFIX = "Review productivity for "


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


def norm_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    t = re.sub(r"^review productivity for cla-\d+\s*", "", t)
    return t[:120]


def main() -> None:
    code, issues = api("GET", f"companies/{COMPANY}/issues?limit=500")
    if code != 200:
        raise SystemExit(code)

    by_title: dict[str, list[dict]] = {}
    cancelled = 0

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        if issue.get("status") in ("done", "cancelled"):
            continue
        title = issue.get("title") or ""
        if title.startswith(PRODUCTIVITY_PREFIX):
            iid = issue["id"]
            ident = issue.get("identifier", iid[:8])
            api(
                "PATCH",
                f"issues/{iid}",
                {
                    "status": "cancelled",
                    "comment": "Cancelled: auto productivity-review noise while Boss queue paused.",
                },
            )
            print(f"  cancel productivity {ident}")
            cancelled += 1
            continue
        key = norm_title(title)
        if len(key) < 8:
            continue
        by_title.setdefault(key, []).append(issue)

    for key, group in by_title.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda i: i.get("issueNumber") or 9999)
        keep = group[0]
        for dup in group[1:]:
            ident = dup.get("identifier")
            keep_id = keep.get("identifier")
            api(
                "PATCH",
                f"issues/{dup['id']}",
                {
                    "status": "cancelled",
                    "comment": f"Duplicate of {keep_id}; cancelled during queue cleanup.",
                },
            )
            print(f"  cancel dup {ident} (keep {keep_id}): {key[:50]}")
            cancelled += 1

    print(f"Cancelled {cancelled} issue(s).")


if __name__ == "__main__":
    main()
