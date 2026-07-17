#!/usr/bin/env python3
"""Print tail of latest heartbeat run log."""
import json
import os
import urllib.request

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)


def main() -> None:
    url = f"{API}/companies/{COMPANY}/heartbeat-runs?limit=1"
    with urllib.request.urlopen(url, timeout=30) as resp:
        runs = json.load(resp)
    run = runs[0] if isinstance(runs, list) else runs["items"][0]
    rid = run["id"]
    print(f"run={rid} status={run.get('status')} code={run.get('errorCode')}")
    log_url = f"{API}/heartbeat-runs/{rid}/log?limitBytes=12000"
    with urllib.request.urlopen(log_url, timeout=30) as resp:
        log = resp.read().decode("utf-8", errors="replace")
    print(log[-4000:] if len(log) > 4000 else log)


if __name__ == "__main__":
    main()
