#!/usr/bin/env python3
"""Apply GMAIL_* lines from a paste file into /docker/clawsum/.env (no printing secrets)."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ENV = Path("/docker/clawsum/.env")
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/gmail-oauth-paste.env")

KEYS = {
    "GMAIL_ADMIN_ADDRESS",
    "GMAIL_CLIENT_ID",
    "GMAIL_CLIENT_SECRET",
    "GMAIL_REFRESH_TOKEN",
    "GMAIL_BACKFILL_MAX",
    "GMAIL_SYNC_QUERY",
    "GMAIL_INCREMENTAL_QUERY",
}

def parse(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in KEYS and v:
            out[k] = v
    return out

def upsert(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    seen = set()
    out = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n")

def main() -> int:
    updates = parse(SRC.read_text(encoding="utf-8", errors="replace"))
    need = ["GMAIL_REFRESH_TOKEN", "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET"]
    missing = [k for k in need if k not in updates]
    if missing:
        print("missing:", ", ".join(missing), file=sys.stderr)
        return 1
    upsert(ENV, updates)
    print("updated", ENV, "keys=", sorted(updates.keys()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
