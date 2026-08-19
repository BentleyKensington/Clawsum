#!/usr/bin/env python3
"""Re-assert CLA-62 todo + media assignee. No restarts."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:3100/api"


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
        return e.code, e.read().decode()


def main() -> int:
    env = load_env()
    cid = env["PAPERCLIP_COMPANY_ID"]
    code, issues = req("GET", f"/companies/{cid}/issues?q=CLA-62")
    issue = next((i for i in issues if i.get("identifier") == "CLA-62"), None) if isinstance(issues, list) else None
    if not issue:
        print("CLA-62 missing")
        return 1
    print("before", issue.get("status"), issue.get("assigneeAgentId"), (issue.get("title") or "")[:50])
    iid = issue["id"]
    code, agents = req("GET", f"/companies/{cid}/agents")
    media = next(
        (
            a
            for a in agents
            if (a.get("adapterConfig") or {}).get("agentId") == "media"
            or a.get("name") == "Clawsum Media"
        ),
        None,
    ) if isinstance(agents, list) else None
    print("media_agent", media.get("id") if media else None, media.get("name") if media else None)

    code, rec = req("GET", f"/issues/{iid}/recovery-actions")
    active = (rec or {}).get("active") if isinstance(rec, dict) else None
    print("recovery", active.get("kind") if active else None, active.get("id") if active else None)
    if active and active.get("id"):
        code, res = req(
            "POST",
            f"/issues/{iid}/recovery-actions/resolve",
            {
                "actionId": active["id"],
                "outcome": "cancelled",
                "sourceIssueStatus": "todo",
                "resolutionNote": "Phase 0 advanced; clear false disposition block. No service restart.",
            },
        )
        print("resolve", code)

    patch = {"status": "todo"}
    if media:
        patch["assigneeAgentId"] = media["id"]
    code, res = req("PATCH", f"/issues/{iid}", patch)
    print("patch", code, res.get("status") if isinstance(res, dict) else res, res.get("assigneeAgentId") if isinstance(res, dict) else None)

    code, issue2 = req("GET", f"/issues/{iid}")
    if isinstance(issue2, dict):
        print("after", issue2.get("identifier"), issue2.get("status"), issue2.get("assigneeAgentId"))
        ar = issue2.get("activeRecoveryAction")
        print("activeRecovery", ar.get("kind") if isinstance(ar, dict) else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
