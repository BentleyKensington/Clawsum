#!/usr/bin/env python3
"""Print latest Paperclip heartbeat runs."""
import json
import os
import urllib.request

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)


def main() -> None:
    url = f"{API}/companies/{COMPANY}/heartbeat-runs?limit=5"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    runs = data if isinstance(data, list) else data.get("items", data)
    for r in runs[:5]:
        msg = (r.get("errorMessage") or r.get("summary") or "")[:100]
        print(
            f"{r.get('startedAt','?')} {r.get('status','?'):8} "
            f"agent={str(r.get('agentId',''))[:8]} "
            f"code={r.get('errorCode','')} {msg}"
        )


if __name__ == "__main__":
    main()
