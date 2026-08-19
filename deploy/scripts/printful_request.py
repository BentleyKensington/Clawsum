#!/usr/bin/env python3
"""Printful REST helper. Authorization: Bearer $PRINTFUL_API_TOKEN."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from vendor_http import http_json, load_dotenv  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: printful_request.py GET|POST|PUT|DELETE /path [json-body]", file=sys.stderr)
        return 2
    load_dotenv()
    token = (os.environ.get("PRINTFUL_API_TOKEN") or "").strip()
    if len(token) < 8:
        raise SystemExit("PRINTFUL_API_TOKEN missing")
    method, path = sys.argv[1], sys.argv[2]
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE") and os.environ.get("PRINTFUL_ALLOW_MUTATE") != "1":
        print("mutate blocked — set PRINTFUL_ALLOW_MUTATE=1 after Boss Tier 2", file=sys.stderr)
        return 3
    base = os.environ.get("PRINTFUL_API_BASE", "https://api.printful.com").rstrip("/")
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    url = base + (path if path.startswith("/") else "/" + path)
    print(json.dumps(http_json(method, url, {"Authorization": f"Bearer {token}"}, body), indent=2)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
