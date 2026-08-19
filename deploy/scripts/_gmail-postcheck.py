#!/usr/bin/env python3
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
p = svc.users().getProfile(userId="me").execute()
print(
    "POSTCHECK",
    p.get("emailAddress"),
    "messages",
    p.get("messagesTotal"),
    "expiry",
    creds.expiry.isoformat() if creds.expiry else "?",
)
