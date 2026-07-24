#!/usr/bin/env python3
"""Download the newest image/logo attachment from clawsums@gmail.com."""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
OUT_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/clawsum-logo")

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError as e:
    raise SystemExit(f"missing google deps: {e}") from e


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


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico"}
IMAGE_MIME = (
    "image/",
    "application/octet-stream",  # sometimes mislabeled
)


def is_image(filename: str, mime: str) -> bool:
    name = (filename or "").lower()
    mime = (mime or "").lower()
    if any(name.endswith(ext) for ext in IMAGE_EXTS):
        return True
    if mime.startswith("image/"):
        return True
    if "logo" in name or "brand" in name or "crest" in name:
        return True
    return False


def walk_parts(payload: dict):
    yield payload
    for p in payload.get("parts") or []:
        yield from walk_parts(p)


def main() -> int:
    env = load_env()
    for key in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
        if not env.get(key):
            print(f"missing {key}", file=sys.stderr)
            return 1

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

    # Prefer recent mail with attachments; logo keywords help if many mails
    queries = [
        "has:attachment newer_than:1d",
        "has:attachment (logo OR brand OR crest OR clawsum) newer_than:7d",
        "has:attachment newer_than:3d",
    ]
    msg_ids: list[str] = []
    for q in queries:
        res = svc.users().messages().list(userId="me", q=q, maxResults=15).execute()
        for m in res.get("messages") or []:
            mid = m["id"]
            if mid not in msg_ids:
                msg_ids.append(mid)
        if msg_ids:
            break

    if not msg_ids:
        print("No recent messages with attachments found.", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    saved = []

    for mid in msg_ids:
        full = (
            svc.users()
            .messages()
            .get(userId="me", id=mid, format="full")
            .execute()
        )
        headers = {
            h["name"].lower(): h["value"]
            for h in full.get("payload", {}).get("headers", [])
        }
        subject = headers.get("subject", "")
        date = headers.get("date", "")
        print(f"MSG {mid} | {date} | {subject}")

        for part in walk_parts(full.get("payload") or {}):
            body = part.get("body") or {}
            att_id = body.get("attachmentId")
            filename = part.get("filename") or ""
            mime = part.get("mimeType") or ""
            if not att_id:
                continue
            if not is_image(filename, mime):
                print(f"  skip non-image: {filename!r} {mime}")
                continue

            att = (
                svc.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=mid, id=att_id)
                .execute()
            )
            raw = base64.urlsafe_b64decode(att["data"] + "==")
            safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (filename or "logo.bin"))
            if not Path(safe).suffix:
                if "png" in mime:
                    safe += ".png"
                elif "jpeg" in mime or "jpg" in mime:
                    safe += ".jpg"
                elif "svg" in mime:
                    safe += ".svg"
                else:
                    safe += ".bin"
            out = OUT_DIR / f"{mid[:8]}_{safe}"
            out.write_bytes(raw)
            print(f"  SAVED {out} ({len(raw)} bytes) mime={mime}")
            saved.append(str(out))

    if not saved:
        print("Found messages but no image attachments.", file=sys.stderr)
        return 3

    print("DONE")
    for p in saved:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
