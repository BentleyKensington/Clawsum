#!/usr/bin/env python3
"""Reset all blocked Paperclip issues to todo."""
from __future__ import annotations

import json
import os
import urllib.request

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, json.load(resp)


def main() -> None:
    code, issues = api("GET", f"companies/{COMPANY}/issues?status=blocked")
    if not isinstance(issues, list):
        print("No blocked issues list", code)
        return
    ok = 0
    for issue in issues:
        iid = issue["id"]
        title = (issue.get("title") or "")[:50]
        code, _ = api("PATCH", f"issues/{iid}", {"status": "todo"})
        if code == 200:
            ok += 1
        print(f"  {code} {title}")
    print(f"Unblocked {ok}/{len(issues)} issues → todo")


if __name__ == "__main__":
    main()
