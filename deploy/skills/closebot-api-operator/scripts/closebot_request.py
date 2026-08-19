#!/usr/bin/env python3
"""CloseBot REST helper. Reads CLOSEBOT_API_KEY or X_CB_KEY. Never prints the key."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("CLOSEBOT_API_BASE", "https://api.closebot.com").rstrip("/")


def load_dotenv() -> None:
    env_path = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum")) / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def key() -> str:
    load_dotenv()
    k = (os.environ.get("CLOSEBOT_API_KEY") or os.environ.get("X_CB_KEY") or "").strip()
    if len(k) < 8:
        raise SystemExit("CLOSEBOT_API_KEY missing")
    return k


def request(method: str, path: str, body: dict | None = None) -> object:
    url = BASE + (path if path.startswith("/") else "/" + path)
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers={
            "X-CB-KEY": key(),
            "Accept": "application/json",
            "User-Agent": "Clawsum-CloseBot/1.0",
        },
    )
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {"ok": True, "status": resp.status}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {path} → {e.code}: {err[:500]}") from e


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: closebot_request.py GET|POST|PUT|DELETE /path [json-body]", file=sys.stderr)
        return 2
    method, path = sys.argv[1], sys.argv[2]
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE") and os.environ.get("CLOSEBOT_ALLOW_MUTATE") != "1":
        print("mutate blocked — set CLOSEBOT_ALLOW_MUTATE=1 after Boss Tier 2", file=sys.stderr)
        return 3
    print(json.dumps(request(method, path, body), indent=2)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
