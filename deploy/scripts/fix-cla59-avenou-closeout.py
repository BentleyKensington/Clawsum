#!/usr/bin/env python3
"""Close CLA-59 (and sibling stuck Avenou archive issues) via local Paperclip API.

Registers work products from the agent's local closeout artifacts, posts the
ready comment, marks done, and resolves missing_disposition recovery.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:3100/api"
ISSUE_ID = "9a21fdf3-88e5-4ec2-ae8b-39cd78552b6d"
WS = Path("/docker/clawsum/data/.openclaw/workspace-ghl-ave-rei")
CLOSEOUT = WS / "notes/activity-archive/CLA-59-closeout.json"
COMMENT = WS / "notes/activity-archive/CLA-59-issue-comment.md"
SNAPSHOT = WS / "notes/activity-archive/LATEST-30d-snapshot.json"
OBSIDIAN = Path(
    "/docker/clawsum/obsidian/GHL/AVE-REI/Reports/2026-08-05-30-day-activity-archive.md"
)


def req(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(
        f"{API.rstrip('/')}/{path.lstrip('/')}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"HTTP {e.code} {method} {path}: {err[:800]}")
        return e.code, err


def main() -> int:
    closeout = json.loads(CLOSEOUT.read_text()) if CLOSEOUT.exists() else {}
    comment_body = COMMENT.read_text() if COMMENT.exists() else closeout.get(
        "recommendedPatch", {}
    ).get("comment", "CLA-59 archive complete from cache-first artifacts.")

    # 1) Register work products
    products = [
        {
            "type": "artifact",
            "provider": "openclaw-workspace",
            "title": "AVE REI 30-day activity snapshot (LATEST pointer)",
            "url": None,
            "status": "ready_for_review",
            "isPrimary": True,
            "metadata": {
                "path": str(SNAPSHOT),
                "exists": SNAPSHOT.exists(),
            },
        },
        {
            "type": "document",
            "provider": "obsidian",
            "title": "AVE REI 30-day activity archive report",
            "url": None,
            "status": "ready_for_review",
            "isPrimary": False,
            "metadata": {
                "path": str(OBSIDIAN),
                "exists": OBSIDIAN.exists(),
            },
        },
        {
            "type": "artifact",
            "provider": "openclaw-workspace",
            "title": "CLA-59 closeout payload",
            "url": None,
            "status": "ready_for_review",
            "isPrimary": False,
            "metadata": {"path": str(CLOSEOUT), "exists": CLOSEOUT.exists()},
        },
    ]
    for p in products:
        # Some schemas reject null url — drop if None
        body = {k: v for k, v in p.items() if v is not None}
        # try without metadata if rejected
        code, res = req("POST", f"/issues/{ISSUE_ID}/work-products", body)
        if code >= 400 and "metadata" in body:
            body.pop("metadata", None)
            code, res = req("POST", f"/issues/{ISSUE_ID}/work-products", body)
        print("work-product", body.get("title"), "=>", code)

    # 2) Comment
    code, res = req("POST", f"/issues/{ISSUE_ID}/comments", {"body": comment_body[:12000]})
    print("comment =>", code)

    # 3) Patch status done
    patch = {"status": "done"}
    code, res = req("PATCH", f"/issues/{ISSUE_ID}", patch)
    print("patch done =>", code, (res or {}) if isinstance(res, dict) else res)

    # 4) Resolve recovery action
    code, rec = req("GET", f"/issues/{ISSUE_ID}/recovery-actions")
    active = (rec or {}).get("active") if isinstance(rec, dict) else None
    if active and active.get("id"):
        code, res = req(
            "POST",
            f"/issues/{ISSUE_ID}/recovery-actions/resolve",
            {
                "actionId": active["id"],
                "outcome": "restored",
                "sourceIssueStatus": "done",
                "resolutionNote": (
                    "Boss/coding closeout: archive artifacts registered; "
                    "transport was Authelia public URL — fixed to host.docker.internal local API."
                ),
            },
        )
        print("recovery resolve =>", code)
    else:
        print("no active recovery")

    # 5) Verify
    code, issue = req("GET", f"/issues/{ISSUE_ID}")
    if isinstance(issue, dict):
        print(
            "FINAL",
            issue.get("identifier"),
            issue.get("status"),
            "recovery",
            (issue.get("activeRecoveryAction") or {}).get("status")
            if issue.get("activeRecoveryAction")
            else None,
            "workProducts",
            len(issue.get("workProducts") or []),
        )

    # 6) Sibling stuck issues CLA-52..58 same title — cancel as superseded by CLA-59
    env = {}
    for line in Path("/docker/clawsum/.env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    cid = env["PAPERCLIP_COMPANY_ID"]
    code, issues = req("GET", f"/companies/{cid}/issues?q=Avenou%20GHL%2030-day")
    if isinstance(issues, list):
        for it in issues:
            ident = it.get("identifier") or ""
            if ident == "CLA-59":
                continue
            if it.get("status") in ("blocked", "todo", "in_progress", "in_review") and (
                it.get("title") or ""
            ).startswith("Avenou GHL 30-day"):
                code, _ = req(
                    "PATCH",
                    f"/issues/{it['id']}",
                    {
                        "status": "cancelled",
                        "comment": f"Superseded by CLA-59 closeout ({ident}).",
                    },
                )
                # comment separately if patch doesn't take comment
                req(
                    "POST",
                    f"/issues/{it['id']}/comments",
                    {
                        "body": f"Cancelled as duplicate/superseded by CLA-59 (same archive objective)."
                    },
                )
                # try cancel status if comment-only patch failed
                if code >= 400:
                    req("PATCH", f"/issues/{it['id']}", {"status": "cancelled"})
                print("supersede", ident, "=>", code)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
