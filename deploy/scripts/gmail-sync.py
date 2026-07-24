#!/usr/bin/env python3
"""
Sync Gmail inbox (and optional backfill) into Postgres ops.emails.

Requires Google Cloud OAuth desktop credentials + refresh token in .env:
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
  GMAIL_ADMIN_ADDRESS (mailbox to monitor)

Usage:
  python3 gmail-sync.py              # incremental since last sync
  python3 gmail-sync.py --backfill   # pull up to GMAIL_BACKFILL_MAX messages (default 500)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"

try:
    import psycopg2
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError as e:
    print(
        "Missing deps. On VPS: pip3 install --break-system-packages "
        "google-auth google-auth-oauthlib google-api-python-client psycopg2-binary",
        file=sys.stderr,
    )
    raise SystemExit(1) from e


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def pg_conn(env: dict):
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        dbname=env.get("POSTGRES_DB", "clawsum"),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
    )


def gmail_service(env: dict):
    creds = Credentials(
        token=None,
        refresh_token=env["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=env["GMAIL_CLIENT_ID"],
        client_secret=env["GMAIL_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def decode_body(payload: dict) -> str:
    texts = []

    def walk(part: dict):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data and mime.startswith("text/plain"):
            texts.append(base64.urlsafe_b64decode(data + "==").decode(errors="replace"))
        for sub in part.get("parts") or []:
            walk(sub)

    if payload.get("body", {}).get("data"):
        walk(payload)
    else:
        for part in payload.get("parts") or []:
            walk(part)
    return "\n".join(texts)[:50000]


def header_map(headers: list) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in headers}


def guess_domain(subject: str, from_addr: str, body: str) -> str | None:
    blob = f"{subject} {from_addr} {body}".lower()
    rules = [
        ("coding", "coding"),
        ("realestate", "realestate"),
        ("real estate", "realestate"),
        ("ghl", "ghl"),
        ("gohighlevel", "ghl"),
        ("comms", "comms"),
        ("research", "research"),
        ("planning", "planning"),
        ("data", "data"),
        ("scraper", "data"),
    ]
    for acc in __import__("ghl_accounts", fromlist=["accounts"]).accounts():
        for needle in acc.get("telegram_needles", []):
            rules.insert(0, (needle.lower(), acc["id"]))
    for needle, domain in rules:
        if needle in blob:
            return domain
    return None


def upsert_email(cur, msg: dict, full: dict | None = None, mailbox: str = "clawsums@gmail.com"):
    payload = (full or msg).get("payload", {})
    headers = header_map(payload.get("headers", []))
    from_addr = headers.get("from", "")
    to_addrs = headers.get("to", "")
    cc_addrs = headers.get("cc", "")
    subject = headers.get("subject", "(no subject)")
    labels = msg.get("labelIds") or []
    internal_date = int(msg.get("internalDate", 0)) / 1000
    received_at = datetime.fromtimestamp(internal_date, tz=timezone.utc)
    snippet = msg.get("snippet", "")
    body_text = decode_body(payload) if full else ""
    domain = guess_domain(subject, from_addr, body_text or snippet)

    cur.execute(
        """
        INSERT INTO ops.emails (
          gmail_id, thread_id, from_addr, to_addrs, cc_addrs, subject, snippet, body_text,
          labels, is_inbox, is_sent, received_at, domain_guess, raw_headers, mailbox
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (gmail_id) DO UPDATE SET
          snippet = EXCLUDED.snippet,
          body_text = COALESCE(NULLIF(EXCLUDED.body_text,''), ops.emails.body_text),
          labels = EXCLUDED.labels,
          mailbox = COALESCE(ops.emails.mailbox, EXCLUDED.mailbox),
          synced_at = NOW()
        """,
        (
            msg["id"],
            msg.get("threadId"),
            from_addr,
            to_addrs,
            cc_addrs,
            subject,
            snippet,
            body_text,
            json.dumps(labels),
            "INBOX" in labels,
            "SENT" in labels,
            received_at,
            domain,
            json.dumps(headers),
            mailbox,
        ),
    )


def list_message_ids(service, query: str, max_results: int) -> list[str]:
    ids: list[str] = []
    page_token = None
    while len(ids) < max_results:
        batch = min(100, max_results - len(ids))
        res = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=batch, pageToken=page_token)
            .execute()
        )
        for m in res.get("messages", []):
            ids.append(m["id"])
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true")
    args = parser.parse_args()

    env = load_env()
    for key in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
        if not env.get(key):
            print(f"ERROR: {key} missing in .env — see docs/GMAIL-ADMIN-SETUP.md", file=sys.stderr)
            sys.exit(1)

    max_backfill = int(env.get("GMAIL_BACKFILL_MAX", "500"))
    account = env.get("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com")
    mailbox = account

    service = gmail_service(env)
    conn = pg_conn(env)
    cur = conn.cursor()

    if args.backfill:
        query = env.get("GMAIL_SYNC_QUERY", "in:all")
        print(f"Backfill query={query!r} max={max_backfill} mailbox={mailbox}")
        ids = list_message_ids(service, query, max_backfill)
    else:
        # Last 48h inbox + anything with Clawsum label if used
        query = env.get("GMAIL_INCREMENTAL_QUERY", "newer_than:2d")
        ids = list_message_ids(service, query, 200)

    inserted = 0
    for i, mid in enumerate(ids):
        msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
        upsert_email(cur, msg, msg, mailbox=mailbox)
        inserted += 1
        if (i + 1) % 50 == 0:
            conn.commit()
            print(f"  synced {i + 1}/{len(ids)}")

    cur.execute(
        """
        UPDATE ops.email_sync_state SET
          last_sync_at = NOW(),
          messages_total = (SELECT COUNT(*) FROM ops.emails),
          backfill_completed = %s
        WHERE id = 1
        """,
        (args.backfill,),
    )
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM ops.emails WHERE processing_status = 'pending'")
    pending = cur.fetchone()[0]
    conn.close()
    print(f"Done. Synced {inserted} messages. Pending triage: {pending}")


if __name__ == "__main__":
    main()
