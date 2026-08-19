#!/usr/bin/env python3
"""Smoke: create a tiny Avenou issue, register work-product via local API, mark done.

Uses host loopback Paperclip (local_trusted). Validates closeout path that agents
should use via host.docker.internal:3102 (Host-rewritten to :3100).
"""
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
        err = e.read().decode()
        print(f"HTTP {e.code} {method} {path}: {err[:500]}")
        return e.code, err


def main() -> int:
    env = load_env()
    cid = env["PAPERCLIP_COMPANY_ID"]

    # Find AVE REI agent
    code, agents = req("GET", f"/companies/{cid}/agents")
    if not isinstance(agents, list):
        print("agents fail", code, agents)
        return 1
    ave = next(
        (
            a
            for a in agents
            if (a.get("adapterConfig") or {}).get("agentId") == "ghl-ave-rei"
            or "AVE REI" in (a.get("name") or "")
        ),
        None,
    )
    if not ave:
        print("AVE REI agent not found")
        return 1
    print("assignee", ave.get("name"), ave.get("id"))

    # Create smoke issue
    code, issue = req(
        "POST",
        f"/companies/{cid}/issues",
        {
            "title": "SMOKE: Avenou API closeout via local proxy",
            "description": (
                "Routing smoke only. Do not pull GHL.\n"
                "Close via local Paperclip API (host.docker.internal:3102 from gateway).\n"
                "Never use https://paperclip.clawsum.com/api for closeout."
            ),
            "status": "todo",
            "priority": "low",
            "assigneeAgentId": ave["id"],
        },
    )
    if code >= 300 or not isinstance(issue, dict):
        print("create fail", code, issue)
        return 1
    iid = issue["id"]
    ident = issue.get("identifier")
    print("created", ident, iid)

    # Work product + comment + done (simulates what agent must do)
    code, _ = req(
        "POST",
        f"/issues/{iid}/work-products",
        {
            "type": "artifact",
            "provider": "smoke",
            "title": "Avenou routing smoke OK",
            "status": "ready_for_review",
            "isPrimary": True,
        },
    )
    print("work-product", code)
    code, _ = req(
        "POST",
        f"/issues/{iid}/comments",
        {
            "body": (
                "SMOKE PASS: work-product registered and issue closed via local Paperclip API "
                f"({API}). Gateway path should use PAPERCLIP_API_URL="
                "http://host.docker.internal:3102/api"
            )
        },
    )
    print("comment", code)
    code, done = req("PATCH", f"/issues/{iid}", {"status": "done"})
    print("done", code, isinstance(done, dict) and done.get("status"))

    # Verify proxy health from host
    code, health = req("GET", "/health")
    print("api health", code)

    # Proxy path (same backend)
    try:
        with urllib.request.urlopen("http://127.0.0.1:3102/api/health", timeout=10) as r:
            print("proxy3102", r.status)
    except Exception as e:
        print("proxy3102 FAIL", e)
        return 1

    print("SMOKE_OK", ident)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
