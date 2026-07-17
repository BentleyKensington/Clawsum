#!/usr/bin/env python3
import json
import urllib.request

API = "http://127.0.0.1:3100/api"
CID = ""


def main() -> None:
    issues = json.load(
        urllib.request.urlopen(f"{API}/companies/{CID}/issues?limit=500")
    )
    by_ident = {i["identifier"]: i for i in issues if i.get("identifier")}
    todo = sum(1 for i in issues if i.get("status") == "todo")
    blocked = sum(1 for i in issues if i.get("status") == "blocked")
    with_assignee = sum(1 for i in issues if i.get("assigneeAgentId"))
    analyzed = sum(
        1 for i in issues if "<!-- clawsum-analyzed:" in (i.get("description") or "")
    )
    print(f"Issues: todo={todo} blocked={blocked} with_assignee={with_assignee} analyzed={analyzed}")
    for ident in ["CLA-41", "CLA-2", "CLA-31", "CLA-8"]:
        i = by_ident.get(ident)
        if not i:
            print(f"  {ident}: missing")
            continue
        comments = json.load(
            urllib.request.urlopen(f"{API}/issues/{i['id']}/comments")
        )
        nq = sum(1 for c in comments if "Boss — clarification" in (c.get("body") or ""))
        print(
            f"  {ident}: {i['status']} assignee={bool(i.get('assigneeAgentId'))} "
            f"boss_comments={nq} total_comments={len(comments)}"
        )


if __name__ == "__main__":
    main()
