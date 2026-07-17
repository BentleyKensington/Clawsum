#!/usr/bin/env python3
"""Approve all pending gateway device pairing requests (Paperclip backends)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ENV = Path("/docker/clawsum/.env")
IMAGE = os.environ.get("OPENCLAW_IMAGE", "ghcr.io/openclaw/openclaw:2026.6.10")
GW_WS = "ws://127.0.0.1:18789"


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("OPENCLAW_GATEWAY_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENCLAW_GATEWAY_TOKEN missing")


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
    out = (r.stdout or "") + (r.stderr or "")
    return out


def main() -> None:
    listing = run_oc("devices", "list")
    print(listing)
    ids = re.findall(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", listing
    )
    # First UUID per pending row block — dedupe preserving order
    seen = set()
    pending_ids = []
    for uid in ids:
        if uid in seen:
            continue
        seen.add(uid)
        pending_ids.append(uid)
    # Heuristic: pending section UUIDs appear before "Paired" in output
    if "Pending" in listing:
        part = listing.split("Paired", 1)[0]
        pending_ids = list(
            dict.fromkeys(
                re.findall(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                    part,
                )
            )
        )
    approved = 0
    for rid in pending_ids:
        out = run_oc("devices", "approve", rid)
        print(out)
        if "approved" in out.lower() or "paired" in out.lower():
            approved += 1
    # Scope-upgrade requests (CLI / Paperclip need operator.pairing)
    for rid in re.findall(
        r"requestId:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        listing,
    ):
        out = run_oc("devices", "approve", rid)
        print(out)
        if "approved" in out.lower():
            approved += 1
    print(f"Approved {approved} device request(s).")
    final = run_oc("devices", "list")
    print(final)
    for rid in re.findall(
        r"requestId:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        final,
    ):
        print("Approving scope upgrade:", rid)
        print(run_oc("devices", "approve", rid))


if __name__ == "__main__":
    main()
