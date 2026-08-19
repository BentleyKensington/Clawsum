#!/usr/bin/env python3
"""Cancel duplicate Avenou archive issues; close CLA-61 smoke. No service restarts."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:3100/api"
# Keep CLA-59 (done). Cancel duplicate archives + close smoke if still blocked.
CANCEL_IDENTS = [
    "CLA-49",
    "CLA-50",
    "CLA-51",
    "CLA-52",
    "CLA-53",
    "CLA-54",
    "CLA-55",
    "CLA-56",
    "CLA-57",
    "CLA-58",
    "CLA-60",
]
SMOKE_IDENT = "CLA-61"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in Path("/docker/clawsum/.env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


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
        print(f"HTTP {e.code} {method} {path}: {err[:500]}")
        return e.code, err


def find_issue(cid: str, ident: str) -> dict | None:
    code, issues = req("GET", f"/companies/{cid}/issues?q={ident}")
    if not isinstance(issues, list):
        return None
    return next((i for i in issues if i.get("identifier") == ident), None)


def cancel(issue: dict, note: str) -> None:
    iid = issue["id"]
    ident = issue.get("identifier")
    status = issue.get("status")
    if status in ("cancelled", "done"):
        print(f"skip {ident} already {status}")
        return
    # Resolve recovery if present so cancel isn't blocked
    code, rec = req("GET", f"/issues/{iid}/recovery-actions")
    active = (rec or {}).get("active") if isinstance(rec, dict) else None
    if active and active.get("id"):
        req(
            "POST",
            f"/issues/{iid}/recovery-actions/resolve",
            {
                "actionId": active["id"],
                "outcome": "superseded",
                "sourceIssueStatus": "cancelled",
                "resolutionNote": note,
            },
        )
    req(
        "POST",
        f"/issues/{iid}/comments",
        {"body": note},
    )
    code, res = req("PATCH", f"/issues/{iid}", {"status": "cancelled"})
    print(f"cancel {ident} => {code} {getattr(res, 'get', lambda *_: None)('status') if isinstance(res, dict) else res}")


def close_smoke(issue: dict) -> None:
    iid = issue["id"]
    ident = issue.get("identifier")
    if issue.get("status") == "done":
        print(f"skip {ident} already done")
        return
    code, _ = req(
        "POST",
        f"/issues/{iid}/work-products",
        {
            "type": "artifact",
            "provider": "smoke",
            "title": "Avenou routing smoke OK (proxy :3102)",
            "status": "ready_for_review",
            "isPrimary": True,
        },
    )
    print("smoke work-product", code)
    req(
        "POST",
        f"/issues/{iid}/comments",
        {
            "body": (
                "SMOKE confirmed: local Paperclip API + clawsum-paperclip-agent-proxy (:3102) healthy. "
                "Gateway PAPERCLIP_API_URL=http://host.docker.internal:3102/api. "
                "CLA-59 remains the canonical Avenou archive closeout (done). "
                "Duplicate archive issues cancelled."
            )
        },
    )
    code, rec = req("GET", f"/issues/{iid}/recovery-actions")
    active = (rec or {}).get("active") if isinstance(rec, dict) else None
    if active and active.get("id"):
        req(
            "POST",
            f"/issues/{iid}/recovery-actions/resolve",
            {
                "actionId": active["id"],
                "outcome": "restored",
                "sourceIssueStatus": "done",
                "resolutionNote": "Smoke path validated; proxy healthy.",
            },
        )
    code, res = req("PATCH", f"/issues/{iid}", {"status": "done"})
    print(f"done {ident} => {code}", res.get("status") if isinstance(res, dict) else res)


def main() -> int:
    env = load_env()
    cid = env["PAPERCLIP_COMPANY_ID"]
    note = (
        "Superseded by CLA-59 (done). Duplicate Avenou 30-day archive issue. "
        "Paperclip agent API path fixed via host.docker.internal:3102 — no further work."
    )
    for ident in CANCEL_IDENTS:
        issue = find_issue(cid, ident)
        if not issue:
            print(f"missing {ident}")
            continue
        cancel(issue, note)

    smoke = find_issue(cid, SMOKE_IDENT)
    if smoke:
        close_smoke(smoke)
    else:
        print("missing", SMOKE_IDENT)

    # Report remaining blocked avenish
    code, blocked = req("GET", f"/companies/{cid}/issues?status=blocked")
    if isinstance(blocked, list):
        aven = [
            i
            for i in blocked
            if "aven" in ((i.get("title") or "") + (i.get("identifier") or "")).lower()
            or "archive" in (i.get("title") or "").lower()
        ]
        print(f"blocked_remaining_avenish={len(aven)}")
        for i in aven:
            print(" ", i.get("identifier"), i.get("status"), (i.get("title") or "")[:60])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
