#!/usr/bin/env python3
"""Invoke gmail_triage graph via LangGraph API (Tier 2 smoke test)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:8123"


def main() -> None:
    payload = {
        "assistant_id": "gmail_triage",
        "input": {"email_id": "smoke-test", "status": "new"},
    }
    req = urllib.request.Request(
        f"{API}/runs/wait",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"FAIL HTTP {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"FAIL connect: {e}", file=sys.stderr)
        sys.exit(1)

    print("OK gmail_triage run:", json.dumps(body)[:300])
    print("Tier 2 LangGraph smoke passed")


if __name__ == "__main__":
    main()
