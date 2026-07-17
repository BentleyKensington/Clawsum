#!/usr/bin/env python3
"""Create Paperclip issues from a JSON task list (Boss UI alternative for bulk intake)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import ghl_accounts as ghl

API = "http://127.0.0.1:3100/api"


def company_id() -> str:
    from instance_config import paperclip_company_id
    return paperclip_company_id()


def dept_to_agent() -> dict[str, str]:
    mapping = {
        "admin": "Clawsum Admin",
        "ops": "Clawsum Admin",
        "coding": "Clawsum Coding",
        "code": "Clawsum Coding",
        "data": "Clawsum Data",
        "re": "Clawsum RE",
        "realestate": "Clawsum RE",
        "real estate": "Clawsum RE",
        "comms": "Clawsum Comms",
        "research": "Clawsum Research",
        "planning": "Clawsum Planning",
        "paperclip": "Clawsum Paperclip",
        "hermes": "Clawsum Hermes",
    }
    for acc in ghl.accounts():
        mapping[acc["id"]] = acc["paperclip_name"]
        mapping[acc["slug"]] = acc["paperclip_name"]
    mapping["ghl"] = ghl.accounts()[0]["paperclip_name"] if ghl.accounts() else "Clawsum Admin"
    return mapping


def api(method: str, path: str, body: dict | None = None):
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {"error": e.reason}
        except json.JSONDecodeError:
            payload = {"error": raw}
        return e.code, payload


def agent_map(company_id: str) -> dict[str, str]:
    _, agents = api("GET", f"companies/{company_id}/agents")
    return {a["name"]: a["id"] for a in agents if isinstance(a, dict)}


def resolve_assignee(dept: str, by_name: dict[str, str]) -> str | None:
    key = (dept or "").strip().lower()
    name = dept_to_agent().get(key)
    return by_name.get(name) if name else None


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: paperclip-create-tasks.py tasks.json")
        print('JSON: [{"title":"...","description":"...","department":"coding","priority":"high"}]')
        sys.exit(1)

    tasks = json.loads(Path(sys.argv[1]).read_text())
    if not isinstance(tasks, list):
        raise SystemExit("Expected JSON array of tasks")

    cid = company_id()
    by_name = agent_map(cid)
    created = 0
    for t in tasks:
        title = t.get("title") or t.get("name")
        if not title:
            continue
        assignee = t.get("assigneeAgentId")
        if not assignee and t.get("department"):
            assignee = resolve_assignee(t["department"], by_name)
        body = {
            "title": title,
            "description": t.get("description", ""),
            "status": t.get("status", "todo"),
            "priority": t.get("priority", "medium"),
        }
        if assignee:
            body["assigneeAgentId"] = assignee
        code, res = api("POST", f"companies/{cid}/issues", body)
        if code in (200, 201):
            created += 1
            print(f"OK  {title} -> {res.get('id', res)}")
        else:
            print(f"ERR {title}: {code} {res}", file=sys.stderr)

    print(f"Created {created}/{len(tasks)} issues. Open Boss UI: http://localhost:3100 (via SSH tunnel)")


if __name__ == "__main__":
    main()
