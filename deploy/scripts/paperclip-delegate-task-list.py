#!/usr/bin/env python3
"""
Split a parent Paperclip issue (operator task list) into child issues per line/section.

Usage:
  python3 paperclip-delegate-task-list.py --issue-id <uuid>
  python3 paperclip-delegate-task-list.py --issue CLA-1 --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = __import__("pathlib").Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

API = "http://127.0.0.1:3100/api"


def company_id() -> str:
    from instance_config import paperclip_company_id
    return paperclip_company_id()


def dept_rules() -> list[tuple[str, list[str]]]:
    rules: list[tuple[str, list[str]]] = []
    for acc in ghl.accounts():
        rules.append((acc["id"], list(acc.get("telegram_needles", []))))
    rules.extend(
        [
            ("realestate", ["real estate", "realestate", "property", "deal"]),
            ("coding", ["script", "mcp", "deploy", "infra", "docker", "ci"]),
            ("data", ["etl", "scraper", "analytics", "report"]),
            ("comms", ["whatsapp", "sms template", "messaging"]),
            ("planning", ["roadmap", "priority", "plan"]),
            ("research", ["research", "brief", "investigate"]),
        ]
    )
    return rules


def dept_to_paperclip_name() -> dict[str, str]:
    mapping = {
        "admin": "Clawsum Admin",
        "coding": "Clawsum Coding",
        "data": "Clawsum Data",
        "realestate": "Clawsum RE",
        "comms": "Clawsum Comms",
        "research": "Clawsum Research",
        "planning": "Clawsum Planning",
    }
    for acc in ghl.accounts():
        mapping[acc["id"]] = acc["paperclip_name"]
    return mapping


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"error": raw}
        except json.JSONDecodeError:
            return e.code, {"error": raw}


def agent_map() -> dict[str, str]:
    _, agents = api("GET", f"companies/{company_id()}/agents")
    return {a["name"]: a["id"] for a in agents if isinstance(a, dict)}


DEPT_TO_NAME = dept_to_paperclip_name()


def guess_dept(text: str) -> str:
    low = text.lower()
    for dept, needles in dept_rules():
        if any(n in low for n in needles):
            return dept
    return "admin"


def parse_items(description: str) -> list[str]:
    chunks = re.split(r"\n\s*\n+", description)
    items: list[str] = []
    for c in chunks:
        c = c.strip()
        if not c or c.lower().startswith("please process"):
            continue
        lines = [ln.strip() for ln in c.splitlines() if ln.strip()]
        if len(lines) <= 3 and len(c) < 400:
            items.append(c)
        else:
            for ln in lines:
                ln = re.sub(r"^[-*•]\s*", "", ln).strip()
                if len(ln) > 12:
                    items.append(ln)
    seen = set()
    out = []
    for it in items:
        key = it[:80].lower()
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def resolve_issue(issue_id: str | None, identifier: str | None) -> dict:
    if issue_id:
        code, issue = api("GET", f"issues/{issue_id}")
        if code == 200:
            return issue
    if identifier:
        code, issues = api("GET", f"companies/{company_id()}/issues?limit=500")
        if code == 200 and isinstance(issues, list):
            for i in issues:
                if i.get("identifier") == identifier:
                    return i
    raise SystemExit("Issue not found")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--issue-id")
    p.add_argument("--issue", help="Identifier e.g. CLA-1")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--mark-parent-done", action="store_true")
    args = p.parse_args()

    parent = resolve_issue(args.issue_id, args.issue)
    parent_id = parent["id"]
    desc = parent.get("description") or ""
    items = parse_items(desc)
    if not items:
        print("No items parsed from description", file=sys.stderr)
        sys.exit(1)

    by_name = agent_map()
    admin_id = by_name.get("Clawsum Admin")
    created = 0
    cid = company_id()

    print(f"Parent: {parent.get('identifier')} — {len(items)} subtasks")
    for it in items:
        dept = guess_dept(it)
        assignee_name = DEPT_TO_NAME.get(dept, "Clawsum Admin")
        assignee_id = by_name.get(assignee_name)
        title = it.split("\n")[0][:200]
        body = {
            "title": title,
            "description": (
                f"Delegated from {parent.get('identifier')}\n\n"
                f"{it}\n\n"
                f"Ask operator for clarification if scope unclear. "
                f"Mark done or snooze in Paperclip when complete."
            ),
            "status": "todo",
            "priority": "medium",
            "parentId": parent_id,
        }
        if assignee_id:
            body["assigneeAgentId"] = assignee_id
        if args.dry_run:
            print(f"  [dry-run] {assignee_name}: {title[:70]}")
            created += 1
            continue
        code, res = api("POST", f"companies/{cid}/issues", body)
        if code in (200, 201):
            created += 1
            print(f"  OK {assignee_name}: {title[:60]}")
        else:
            print(f"  ERR {title[:40]}: {code} {res}", file=sys.stderr)

    if not args.dry_run and args.mark_parent_done and admin_id:
        api("PATCH", f"issues/{parent_id}", {"status": "done"})
    elif not args.dry_run and admin_id:
        api(
            "PATCH",
            f"issues/{parent_id}",
            {
                "status": "in_review",
                "description": desc
                + f"\n\n---\nDelegated {created} subtasks on "
                + __import__("datetime")
                .datetime.now(__import__("datetime").timezone.utc)
                .isoformat()
                + "Z",
            },
        )

    print(f"Created {created}/{len(items)} child tasks.")


if __name__ == "__main__":
    main()
