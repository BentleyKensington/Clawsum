#!/usr/bin/env python3
"""Inspect Gmail OAuth health + recent Google verification mail."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ENV_FILE = Path("/docker/clawsum/.env")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if v})
    return out


def main() -> None:
    env = load_env()
    creds = Credentials(
        token=None,
        refresh_token=env["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=env["GMAIL_CLIENT_ID"],
        client_secret=env["GMAIL_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    creds.refresh(Request())
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)

    hp = Path("/docker/clawsum/data/reports/gmail-oauth-health.json")
    print("=== health json ===")
    print(hp.read_text() if hp.exists() else "(none)")

    queries = [
        "newer_than:7d from:google.com",
        "newer_than:7d from:accounts.google.com",
        'newer_than:7d (subject:OAuth OR subject:verification OR subject:verified OR subject:branding OR subject:"Auth Platform")',
        "newer_than:1d",
    ]
    print("=== recent mail ===")
    for q in queries:
        res = svc.users().messages().list(userId="me", q=q, maxResults=8).execute()
        ids = res.get("messages") or []
        print(f"Q {q!r} estimate={res.get('resultSizeEstimate')} listed={len(ids)}")
        for m in ids[:6]:
            full = (
                svc.users()
                .messages()
                .get(
                    userId="me",
                    id=m["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )
            hdrs = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
            print(
                " -",
                (hdrs.get("Date") or "")[:32],
                "|",
                (hdrs.get("From") or "")[:56],
                "|",
                (hdrs.get("Subject") or "")[:90],
            )

    print("=== token artifacts ===")
    skip = {".git", "node_modules", "vendor", ".cache"}
    for root, dirs, files in os.walk("/docker/clawsum"):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if "token" in f.lower() and f.endswith((".json", ".yaml", ".yml")):
                fp = os.path.join(root, f)
                try:
                    st = os.stat(fp)
                    print(
                        fp,
                        "mtime",
                        datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                        "bytes",
                        st.st_size,
                    )
                except OSError:
                    pass


if __name__ == "__main__":
    main()
