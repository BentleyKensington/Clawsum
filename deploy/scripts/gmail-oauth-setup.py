#!/usr/bin/env python3
"""
One-time Gmail OAuth setup for clawsums@gmail.com (read-only sync).

Run on YOUR PC (browser required):
  pip install google-auth-oauthlib google-auth google-api-python-client
  python gmail-oauth-setup.py path/to/client_secret.json

Downloads client_secret.json from Google Cloud Console:
  APIs & Services → Credentials → OAuth 2.0 Client ID → Desktop app → Download JSON

Prints lines to paste into /docker/clawsum/.env on the VPS.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
ADMIN_EMAIL = "clawsums@gmail.com"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    secret_path = Path(sys.argv[1])
    if not secret_path.exists():
        print(f"File not found: {secret_path}", file=sys.stderr)
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("pip install google-auth-oauthlib google-auth google-api-python-client", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
    print("Opening browser — sign in as", ADMIN_EMAIL)
    print("(Use the Google account that owns clawsums@gmail.com)\n")
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    data = json.loads(secret_path.read_text())
    installed = data.get("installed") or data.get("web") or data

    print("\n# --- Paste into /docker/clawsum/.env on the VPS ---\n")
    print(f"GMAIL_ADMIN_ADDRESS={ADMIN_EMAIL}")
    print(f"GMAIL_CLIENT_ID={installed['client_id']}")
    print(f"GMAIL_CLIENT_SECRET={installed['client_secret']}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("GMAIL_BACKFILL_MAX=2000")
    print("GMAIL_SYNC_QUERY=in:all")
    print("GMAIL_INCREMENTAL_QUERY=newer_than:2d")
    print("\n# Then on VPS:")
    print("# pip3 install --break-system-packages google-auth google-auth-oauthlib google-api-python-client psycopg2-binary")
    print("# python3 /docker/clawsum/scripts/gmail-sync.py --backfill")
    print("# bash /docker/clawsum/scripts/install-gmail-sync-cron.sh")

    # Quick verify
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    c = Credentials(
        None,
        refresh_token=creds.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=installed["client_id"],
        client_secret=installed["client_secret"],
        scopes=SCOPES,
    )
    c.refresh(Request())
    svc = build("gmail", "v1", credentials=c)
    profile = svc.users().getProfile(userId="me").execute()
    print(f"\nVerified mailbox: {profile.get('emailAddress')}")
    if profile.get("emailAddress", "").lower() != ADMIN_EMAIL.lower():
        print(f"WARNING: signed in as {profile.get('emailAddress')}, expected {ADMIN_EMAIL}")


if __name__ == "__main__":
    main()
