#!/usr/bin/env python3
"""Generic vendor REST helper used by VAPI / Printful / Shopify scripts."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv() -> None:
    env_path = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum")) / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def http_json(
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict | None = None,
    timeout: int = 45,
) -> object:
    data = None if body is None else json.dumps(body).encode()
    hdrs = {"Accept": "application/json", "User-Agent": "Clawsum/1.0", **headers}
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {"ok": True, "status": resp.status}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} → {e.code}: {err[:800]}") from e
