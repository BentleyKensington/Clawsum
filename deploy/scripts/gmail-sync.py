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
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

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
    # Process env wins over .env so one-shot overrides work
    # (e.g. GMAIL_SYNC_QUERY=in:inbox GMAIL_BACKFILL_MAX=5000).
    out.update({k: v for k, v in os.environ.items() if v != ""})
    return out


def pg_conn(env: dict):
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        dbname=env.get("POSTGRES_DB", "clawsum"),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
    )


def pg_cursor(conn):
    import psycopg2.extras

    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def gmail_service(env: dict):
    creds = Credentials(
        token=None,
        refresh_token=env["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=env["GMAIL_CLIENT_ID"],
        client_secret=env["GMAIL_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    try:
        creds.refresh(Request())
    except Exception as e:  # noqa: BLE001
        # Alert Boss — do not fail silently in cron
        try:
            from gmail_oauth_health import notify_auth_failure

            notify_auth_failure(e, context="gmail-sync")
        except Exception as alert_err:  # noqa: BLE001
            print(f"WARN: oauth alert hook failed: {alert_err}", file=sys.stderr)
        raise
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


def collect_attachments(payload: dict) -> list[dict]:
    """Return [{filename, mimeType, attachmentId, size}] for downloadable parts."""
    found: list[dict] = []

    def walk(part: dict):
        body = part.get("body") or {}
        filename = part.get("filename") or ""
        att_id = body.get("attachmentId")
        mime = part.get("mimeType") or "application/octet-stream"
        size = body.get("size") or 0
        if filename and att_id:
            found.append(
                {
                    "filename": filename,
                    "mimeType": mime,
                    "attachmentId": att_id,
                    "size": size,
                }
            )
        # inline data without attachmentId (small)
        elif filename and body.get("data"):
            found.append(
                {
                    "filename": filename,
                    "mimeType": mime,
                    "attachmentId": None,
                    "inline_data": body.get("data"),
                    "size": size,
                }
            )
        for sub in part.get("parts") or []:
            walk(sub)

    walk(payload or {})
    return found


def archive_attachments(
    service,
    cur,
    *,
    gmail_id: str,
    payload: dict,
    mailbox: str,
    email_id: int | None,
    person_id: str | None,
    env: dict,
) -> list[dict]:
    """Download Gmail parts → MinIO → ops.media_objects + return attachment metas."""
    try:
        import minio_store
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: minio_store unavailable: {exc}", file=sys.stderr)
        return []

    bucket = env.get("MINIO_BUCKET_ATTACHMENTS", "clawsum-attachments")
    metas: list[dict] = []
    for part in collect_attachments(payload):
        try:
            if part.get("attachmentId"):
                att = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=gmail_id, id=part["attachmentId"])
                    .execute()
                )
                raw = base64.urlsafe_b64decode(att.get("data", "") + "==")
            elif part.get("inline_data"):
                raw = base64.urlsafe_b64decode(part["inline_data"] + "==")
            else:
                continue
            if not raw:
                continue
            # Skip tiny / pointless
            if len(raw) < 32:
                continue
            key = minio_store.gmail_attachment_key(mailbox, gmail_id, part["filename"])
            uploaded = minio_store.upload_bytes(
                raw,
                bucket=bucket,
                object_key=key,
                content_type=part.get("mimeType") or "application/octet-stream",
                filename=part["filename"],
                env=env,
            )
            mid = minio_store.record_media(
                cur,
                uploaded,
                source="gmail",
                source_ref=gmail_id,
                email_id=email_id,
                person_id=person_id,
                meta={"gmail_attachment_id": part.get("attachmentId")},
            )
            metas.append(
                {
                    "filename": part["filename"],
                    "content_type": uploaded.get("content_type"),
                    "size": uploaded.get("size_bytes"),
                    "bucket": uploaded["bucket"],
                    "key": uploaded["object_key"],
                    "uri": uploaded["uri"],
                    "sha256": uploaded.get("sha256"),
                    "kind": uploaded.get("kind"),
                    "media_id": mid,
                }
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"WARN: attachment archive failed gmail_id={gmail_id} file={part.get('filename')}: {exc}",
                file=sys.stderr,
            )
    return metas


def upsert_email(cur, msg: dict, full: dict | None = None, mailbox: str = "clawsums@gmail.com",
                 service=None, env: dict | None = None, archive_media: bool = True):
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

    # Contact upsert (From / To / Cc / body phones+emails)
    person_id = None
    try:
        import clawsum_contacts

        touched = clawsum_contacts.upsert_from_email_headers(
            cur,
            from_addr=from_addr,
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            body_text=body_text,
            source="gmail",
        )
        if touched:
            person_id = touched[0].get("id")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: contact upsert failed: {exc}", file=sys.stderr)

    cur.execute(
        """
        INSERT INTO ops.emails (
          gmail_id, thread_id, from_addr, to_addrs, cc_addrs, subject, snippet, body_text,
          labels, is_inbox, is_sent, received_at, domain_guess, raw_headers, mailbox, person_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (gmail_id) DO UPDATE SET
          snippet = EXCLUDED.snippet,
          body_text = COALESCE(NULLIF(EXCLUDED.body_text,''), ops.emails.body_text),
          labels = EXCLUDED.labels,
          mailbox = COALESCE(ops.emails.mailbox, EXCLUDED.mailbox),
          person_id = COALESCE(EXCLUDED.person_id, ops.emails.person_id),
          synced_at = NOW()
        RETURNING id
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
            person_id,
        ),
    )
    row = cur.fetchone()
    email_id = int(row["id"] if isinstance(row, dict) else row[0]) if row else None

    # MinIO attachments (best-effort)
    if archive_media and service is not None and full is not None:
        metas = archive_attachments(
            service,
            cur,
            gmail_id=msg["id"],
            payload=payload,
            mailbox=mailbox,
            email_id=email_id,
            person_id=person_id,
            env=env or {},
        )
        if metas:
            cur.execute(
                """
                UPDATE ops.emails
                SET attachments = %s::jsonb
                WHERE id = %s
                """,
                (json.dumps(metas), email_id),
            )

    # Arcade email vertex
    try:
        from clawsum_arcade import mirror_email

        mirror_email(
            gmail_id=msg["id"],
            subject=subject,
            from_addr=from_addr,
            received_at=received_at.isoformat(),
            person_id=person_id,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: arcade email mirror failed: {exc}", file=sys.stderr)


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
            try:
                from gmail_oauth_health import notify_auth_failure

                notify_auth_failure(f"missing env {key}", context="gmail-sync")
            except Exception as alert_err:  # noqa: BLE001
                print(f"WARN: oauth alert hook failed: {alert_err}", file=sys.stderr)
            sys.exit(1)

    max_backfill = int(env.get("GMAIL_BACKFILL_MAX", "500"))
    account = env.get("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com")
    mailbox = account

    try:
        service = gmail_service(env)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: Gmail OAuth failed: {e}", file=sys.stderr)
        sys.exit(2)
    conn = pg_conn(env)
    cur = pg_cursor(conn)

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
        upsert_email(cur, msg, msg, mailbox=mailbox, service=service, env=env, archive_media=True)
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
    cur.execute("SELECT COUNT(*) AS n FROM ops.emails WHERE processing_status = 'pending'")
    row = cur.fetchone()
    pending = int(row["n"] if isinstance(row, dict) else row[0])
    conn.close()
    print(f"Done. Synced {inserted} messages. Pending triage: {pending}")


if __name__ == "__main__":
    main()
