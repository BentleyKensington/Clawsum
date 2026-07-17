#!/usr/bin/env python3
"""Approve specific or all pending device requests by ID from devices list."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ENV = Path("/docker/clawsum/.env")
IMAGE = os.environ.get("OPENCLAW_IMAGE", "ghcr.io/openclaw/openclaw:2026.6.10")
GW_WS = "ws://127.0.0.1:18789"

# Known stuck requests (updated by devices list output)
EXTRA = [
    "37d7d98c-990f-4195-80e9-f10cac4c2359",
    "2e222961-8f9c-4c75-be92-46909083a26f",
]


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("OPENCLAW_GATEWAY_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")


def run_oc(*args: str) -> str:
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "container:clawsum-openclaw-gateway-1",
        "-v",
        "/docker/clawsum/data/.openclaw:/home/node/.openclaw",
        "-e",
        "HOME=/home/node",
        "-e",
        "OPENCLAW_STATE_DIR=/home/node/.openclaw",
        "-e",
        "OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json",
        IMAGE,
        "node",
        "dist/index.js",
        *args,
        "--url",
        GW_WS,
        "--token",
        token(),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return (r.stdout or "") + (r.stderr or "")


def main() -> None:
    listing = run_oc("devices", "list")
    ids = []
    if "Pending" in listing:
        part = listing.split("Paired", 1)[0]
        ids = re.findall(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            part,
        )
    for rid in list(dict.fromkeys([*ids, *EXTRA])):
        print(f"Approving {rid}...")
        print(run_oc("devices", "approve", rid))
    print(run_oc("devices", "list"))


if __name__ == "__main__":
    main()
