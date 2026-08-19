#!/usr/bin/env python3
"""Shopify Admin REST helper. X-Shopify-Access-Token."""
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
        print("usage: shopify_request.py GET|POST|PUT|DELETE products.json [json-body]", file=sys.stderr)
        return 2
    load_dotenv()
    store = (os.environ.get("SHOPIFY_STORE") or "").strip().replace("https://", "")
    token = (os.environ.get("SHOPIFY_ADMIN_TOKEN") or "").strip()
    ver = os.environ.get("SHOPIFY_API_VERSION", "2026-07")
    if not store or len(token) < 8:
        raise SystemExit("SHOPIFY_STORE or SHOPIFY_ADMIN_TOKEN missing")
    method, path = sys.argv[1], sys.argv[2]
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE") and os.environ.get("SHOPIFY_ALLOW_MUTATE") != "1":
        print("mutate blocked — set SHOPIFY_ALLOW_MUTATE=1 after Boss Tier 2", file=sys.stderr)
        return 3
    path = path.lstrip("/")
    url = f"https://{store}/admin/api/{ver}/{path}"
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    print(
        json.dumps(
            http_json(method, url, {"X-Shopify-Access-Token": token}, body),
            indent=2,
        )[:8000]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
