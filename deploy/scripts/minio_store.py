#!/usr/bin/env python3
"""
MinIO object store helper for Clawsum media (attachments, wav, transcripts, docs).

Env (from /docker/clawsum/.env):
  MINIO_ENDPOINT=http://127.0.0.1:9000
  MINIO_ROOT_USER / MINIO_ROOT_PASSWORD
  MINIO_BUCKET_ATTACHMENTS=clawsum-attachments
  MINIO_BUCKET_CALLS=clawsum-calls
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    env_path = Path("/docker/clawsum/.env")
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if v != ""})
    return out


def _client(env: dict[str, str] | None = None):
    env = env or _load_env()
    try:
        from minio import Minio  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "minio package required: pip3 install --break-system-packages minio"
        ) from exc
    endpoint = env.get("MINIO_ENDPOINT", "http://127.0.0.1:9000")
    parsed = urlparse(endpoint)
    host = parsed.netloc or parsed.path
    secure = parsed.scheme == "https"
    return Minio(
        host,
        access_key=env.get("MINIO_ROOT_USER", "clawsum"),
        secret_key=env.get("MINIO_ROOT_PASSWORD", "minio_change_me"),
        secure=secure,
    ), env


def ensure_bucket(bucket: str, env: dict[str, str] | None = None) -> None:
    client, _ = _client(env)
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guess_kind(filename: str | None, content_type: str | None) -> str:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return "photo"
    if ctype.startswith("video/") or name.endswith((".mp4", ".mov", ".webm")):
        return "video"
    if ctype.startswith("audio/") or name.endswith((".wav", ".mp3", ".m4a", ".ogg")):
        return "audio"
    if name.endswith((".txt", ".vtt", ".srt")) and "transcript" in name:
        return "transcript"
    if "transcript" in name:
        return "transcript"
    if ctype in ("application/pdf",) or name.endswith((".pdf", ".doc", ".docx")):
        return "document"
    return "attachment"


def upload_bytes(
    data: bytes,
    *,
    bucket: str,
    object_key: str,
    content_type: str = "application/octet-stream",
    filename: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    client, env = _client(env)
    ensure_bucket(bucket, env)
    from io import BytesIO

    bio = BytesIO(data)
    client.put_object(
        bucket,
        object_key,
        bio,
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )
    digest = sha256_bytes(data)
    uri = f"s3://{bucket}/{object_key}"
    return {
        "bucket": bucket,
        "object_key": object_key,
        "uri": uri,
        "content_type": content_type,
        "size_bytes": len(data),
        "sha256": digest,
        "filename": filename,
        "kind": guess_kind(filename, content_type),
    }


def record_media(
    cur,
    uploaded: dict[str, Any],
    *,
    source: str,
    source_ref: str | None = None,
    email_id: int | None = None,
    person_id: str | None = None,
    meta: dict | None = None,
) -> str:
    """Insert/upsert ops.media_objects; return id."""
    import json as _json

    cur.execute(
        """
        INSERT INTO ops.media_objects (
          bucket, object_key, uri, content_type, size_bytes, sha256,
          source, source_ref, email_id, person_id, kind, filename, meta
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        ON CONFLICT (bucket, object_key) DO UPDATE SET
          updated_at = now(),
          size_bytes = EXCLUDED.size_bytes,
          sha256 = EXCLUDED.sha256,
          email_id = COALESCE(EXCLUDED.email_id, ops.media_objects.email_id),
          person_id = COALESCE(EXCLUDED.person_id, ops.media_objects.person_id),
          meta = EXCLUDED.meta
        RETURNING id::text
        """,
        (
            uploaded["bucket"],
            uploaded["object_key"],
            uploaded["uri"],
            uploaded.get("content_type"),
            uploaded.get("size_bytes"),
            uploaded.get("sha256"),
            source,
            source_ref,
            email_id,
            person_id,
            uploaded.get("kind") or "attachment",
            uploaded.get("filename"),
            _json.dumps(meta or {}),
        ),
    )
    row = cur.fetchone()
    mid = row["id"] if isinstance(row, dict) else row[0]
    try:
        from clawsum_arcade import mirror_media

        mirror_media(
            media_id=str(mid),
            uri=uploaded["uri"],
            kind=uploaded.get("kind") or "attachment",
            filename=uploaded.get("filename"),
            person_id=person_id,
            email_gmail_id=source_ref if source == "gmail" else None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: arcade media mirror failed: {exc}", file=sys.stderr)
    return str(mid)


def gmail_attachment_key(mailbox: str, gmail_id: str, filename: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y/%m")
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (filename or "bin"))[:120]
    box = (mailbox or "mail").replace("@", "_at_")
    return f"gmail/{box}/{day}/{gmail_id}/{safe}"


def download_uri_bytes(uri: str, env: dict[str, str] | None = None) -> tuple[bytes, dict[str, Any]]:
    """Fetch bytes from a stored s3://bucket/key URI."""
    if not uri.startswith("s3://"):
        raise ValueError(f"unsupported uri: {uri}")
    path = uri[5:]
    bucket, _, object_key = path.partition("/")
    if not bucket or not object_key:
        raise ValueError(f"invalid s3 uri: {uri}")
    client, env = _client(env)
    resp = client.get_object(bucket, object_key)
    try:
        data = resp.read()
    finally:
        try:
            resp.close()
            resp.release_conn()
        except Exception:
            pass
    meta = {
        "bucket": bucket,
        "object_key": object_key,
        "uri": uri,
        "content_type": getattr(resp, "headers", {}).get("Content-Type", "application/octet-stream"),
    }
    return data, meta
