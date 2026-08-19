#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

env = {}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

cid = env["PAPERCLIP_COMPANY_ID"]
api = "http://127.0.0.1:3100/api"


def get(url: str):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode() or "null")


issues = get(f"{api}/companies/{cid}/issues?q=CLA-59")
issue = next((it for it in issues if it.get("identifier") == "CLA-59"), issues[0] if issues else None)
print("CLA-59", json.dumps({
    "identifier": issue.get("identifier"),
    "id": issue.get("id"),
    "status": issue.get("status"),
    "assigneeAgentId": issue.get("assigneeAgentId"),
    "assigneeId": issue.get("assigneeId"),
    "projectId": issue.get("projectId"),
    "blockedReason": issue.get("blockedReason") or issue.get("blockReason"),
    "checkoutRunId": issue.get("checkoutRunId"),
    "title": issue.get("title"),
}, indent=2))
print("DESC:\n", (issue.get("description") or "")[:1200])
iid = issue["id"]
try:
    comments = get(f"{api}/issues/{iid}/comments")
except Exception as e:
    comments = str(e)
print("comments type", type(comments).__name__, "count", len(comments) if isinstance(comments, list) else comments)
if isinstance(comments, list):
    for c in comments[-5:]:
        print("--- comment ---")
        print((c.get("body") or "")[:600])

print("=== 3101 health/companies ===")
for path in ("/api/health", "/api/companies"):
    try:
        data = get(f"http://127.0.0.1:3101{path}")
        print(path, json.dumps(data)[:400])
    except Exception as e:
        print(path, e)

# Compare companies between 3100 and 3101
try:
    c0 = get("http://127.0.0.1:3100/api/companies")
    c1 = get("http://127.0.0.1:3101/api/companies")
    print("3100 companies", [(c.get("name"), c.get("id")) for c in (c0 if isinstance(c0, list) else [])])
    print("3101 companies", [(c.get("name"), c.get("id")) for c in (c1 if isinstance(c1, list) else [])])
except Exception as e:
    print("company compare", e)
