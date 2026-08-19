#!/usr/bin/env python3
"""Print snippets of today's Google Cloud / security mail (no bodies with codes)."""
from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

env: dict[str, str] = {}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

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

res = svc.users().messages().list(
    userId="me",
    q="newer_than:2d (from:google.com OR from:googlecloud@google.com OR from:cloud-noreply@google.com)",
    maxResults=12,
).execute()

for m in res.get("messages") or []:
    full = (
        svc.users()
        .messages()
        .get(userId="me", id=m["id"], format="full", metadataHeaders=["From", "Subject", "Date"])
        .execute()
    )
    hdrs = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
    print("====")
    print("date   ", hdrs.get("Date"))
    print("from   ", hdrs.get("From"))
    print("subject", hdrs.get("Subject"))
    print("snippet", (full.get("snippet") or "").replace("\n", " ")[:400])
