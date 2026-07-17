#!/usr/bin/env python3
"""
Fix Paperclip heartbeats: upgrade shared device scopes in OpenClaw paired.json.

The Paperclip adapter uses devicePrivateKeyPem tied to device 12e91ddc… which was
approved with only operator.pairing. Heartbeats need admin+write scopes.
"""
from __future__ import annotations

import json
from pathlib import Path

DEVICES = Path("/docker/clawsum/data/.openclaw/devices")
PAPERCLIP_DEVICE_ID = (
    "12e91ddc9528f3a34884ac1df5216040a876ab60636143e54d0fb3d5d8847870"
)
FULL_SCOPES = [
    "operator.admin",
    "operator.read",
    "operator.write",
    "operator.approvals",
    "operator.pairing",
]


def main() -> None:
    paired_path = DEVICES / "paired.json"
    pending_path = DEVICES / "pending.json"

    paired = json.loads(paired_path.read_text())
    if PAPERCLIP_DEVICE_ID not in paired:
        print(f"ERROR: device {PAPERCLIP_DEVICE_ID[:16]}… not in paired.json")
        print("Run: python3 sync-paperclip-device-key.py first")
        raise SystemExit(1)

    entry = paired[PAPERCLIP_DEVICE_ID]
    entry["scopes"] = FULL_SCOPES
    entry["approvedScopes"] = FULL_SCOPES
    tokens = entry.get("tokens") or {}
    if isinstance(tokens.get("operator"), dict):
        tokens["operator"]["scopes"] = FULL_SCOPES
    entry["tokens"] = tokens
    paired[PAPERCLIP_DEVICE_ID] = entry
    paired_path.write_text(json.dumps(paired, indent=2) + "\n")
    print(f"Upgraded {PAPERCLIP_DEVICE_ID[:16]}… scopes to full operator set")

    if pending_path.exists():
        pending = json.loads(pending_path.read_text())
        removed = []
        for rid in list(pending.keys()):
            req = pending[rid]
            if req.get("deviceId") == PAPERCLIP_DEVICE_ID or req.get("isRepair"):
                del pending[rid]
                removed.append(rid)
            elif req.get("clientId") == "gateway-client":
                # Stale Paperclip ephemeral device — not used after sync-paperclip-device-key
                del pending[rid]
                removed.append(rid)
        pending_path.write_text(json.dumps(pending, indent=2) + "\n")
        print(f"Cleared {len(removed)} pending request(s): {removed}")

    print("Done. Next heartbeat should connect (no pairing required).")


if __name__ == "__main__":
    main()
