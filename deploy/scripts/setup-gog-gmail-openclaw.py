#!/usr/bin/env python3
"""Seed gog OAuth client JSON from Clawsum .env for OpenClaw gog skill."""
from __future__ import annotations

import json
import os
from pathlib import Path

ENV = Path("/docker/clawsum/.env")
OUT = Path("/docker/clawsum/data/.openclaw/gog-client-secret.json")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV.exists():
        return out
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> None:
    env = load_env()
    cid = env.get("GMAIL_CLIENT_ID")
    secret = env.get("GMAIL_CLIENT_SECRET")
    if not cid or not secret:
        raise SystemExit("Missing GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET in .env")

    data = {
        "installed": {
            "client_id": cid,
            "client_secret": secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    OUT.chmod(0o600)
    try:
        os.chown(OUT, 1000, 1000)
    except OSError:
        pass
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
