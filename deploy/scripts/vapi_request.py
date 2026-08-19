#!/usr/bin/env python3
"""VAPI REST helper. Authorization: Bearer $VAPI_API_KEY. Mutates need VAPI_ALLOW_MUTATE=1."""
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
        print("usage: vapi_request.py GET|POST|PATCH|DELETE /path [json-body]", file=sys.stderr)
        return 2
    load_dotenv()
    key = (os.environ.get("VAPI_API_KEY") or "").strip()
    if len(key) < 8:
        raise SystemExit("VAPI_API_KEY missing")
    method, path = sys.argv[1], sys.argv[2]
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE") and os.environ.get("VAPI_ALLOW_MUTATE") != "1":
        print("mutate blocked — set VAPI_ALLOW_MUTATE=1 after Boss Tier 2", file=sys.stderr)
        return 3
    base = os.environ.get("VAPI_BASE_URL", "https://api.vapi.ai").rstrip("/")
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    url = base + (path if path.startswith("/") else "/" + path)
    print(json.dumps(http_json(method, url, {"Authorization": f"Bearer {key}"}, body), indent=2)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
