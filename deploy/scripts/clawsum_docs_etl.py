#!/usr/bin/env python3
"""
Document chunk ETL → Postgres + MinIO + ArcadeDB (Document / SourceChunk + Mentions).

Binary stays in MinIO. Chunks + contact mentions go to graph for recall.

Usage:
  python3 clawsum_docs_etl.py --text "Hello Jane jane@x.com" --title "Note"
  python3 clawsum_docs_etl.py --file /path/to/notes.txt --title "Notes"
  python3 clawsum_docs_etl.py --file brief.pdf --title "Brief"   # text extract best-effort
  python3 clawsum_docs_etl.py --backfill-media   # chunk ops.media_objects documents/transcripts
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import clawsum_contacts
import minio_store


def _env() -> dict[str, str]:
    return minio_store._load_env()


def _pg():
    import psycopg2
    import psycopg2.extras

    env = _env()
    conn = psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        dbname=env.get("POSTGRES_DB", "clawsum"),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
    )
    return conn, psycopg2.extras.RealDictCursor


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    i = 0
    n = len(text)
    idx = 0
    while i < n:
        end = min(n, i + size)
        # prefer break on paragraph/sentence
        window = text[i:end]
        if end < n:
            for sep in ("\n\n", ". ", "\n"):
                pos = window.rfind(sep)
                if pos > size // 3:
                    end = i + pos + len(sep)
                    window = text[i:end]
                    break
        chunk = window.strip()
        if chunk:
            chunks.append(
                {
                    "chunk_index": idx,
                    "text": chunk,
                    "char_start": i,
                    "char_end": end,
                }
            )
            idx += 1
        if end >= n:
            break
        i = max(end - overlap, i + 1)
    return chunks


def _read_file_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    ctype = "application/octet-stream"
    name = path.name.lower()
    if name.endswith((".txt", ".md", ".csv", ".json", ".vtt", ".srt", ".log")):
        ctype = "text/plain"
        return raw.decode("utf-8", errors="replace"), ctype
    if name.endswith(".pdf"):
        ctype = "application/pdf"
        try:
            # Optional: pypdf if installed
            from io import BytesIO

            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(BytesIO(raw))
            parts = [(p.extract_text() or "") for p in reader.pages]
            return "\n".join(parts), ctype
        except Exception:
            return raw.decode("utf-8", errors="replace"), ctype
    # fallback latin-1
    return raw.decode("utf-8", errors="replace"), ctype


def ingest_document(
    *,
    title: str,
    text: str,
    source: str = "upload",
    source_ref: str | None = None,
    filename: str | None = None,
    content_type: str = "text/plain",
    upload_bytes: bytes | None = None,
    person_ids: list[str] | None = None,
    meta: dict | None = None,
    chunk_size: int = 900,
) -> dict[str, Any]:
    """Store full doc in MinIO, rows in Postgres, vertices/edges in Arcade."""
    text = (text or "").strip()
    if not text and not upload_bytes:
        raise ValueError("text or upload_bytes required")

    body = upload_bytes if upload_bytes is not None else text.encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    env = _env()
    bucket = env.get("MINIO_BUCKET_DOCS", env.get("MINIO_BUCKET_ATTACHMENTS", "clawsum-attachments"))
    day = datetime.now(timezone.utc).strftime("%Y/%m")
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (filename or title or "doc"))[:100]
    key = f"documents/{source}/{day}/{digest[:12]}_{safe}"

    uploaded = minio_store.upload_bytes(
        body,
        bucket=bucket,
        object_key=key,
        content_type=content_type,
        filename=filename or f"{safe}.txt",
        env=env,
    )

    conn, factory = _pg()
    touched_people: list[str] = list(person_ids or [])
    doc_id = None
    chunk_rows: list[dict] = []

    with conn:
        with conn.cursor(cursor_factory=factory) as cur:
            media_id = minio_store.record_media(
                cur,
                uploaded,
                source=source if source in ("gmail", "call", "upload", "chatgpt", "scrape", "other") else "other",
                source_ref=source_ref,
                meta={"title": title, **(meta or {})},
            )

            # Extract contacts from full text
            extracted = clawsum_contacts.extract_contacts_from_text(text)
            for email in extracted["emails"]:
                r = clawsum_contacts.upsert_person(
                    cur,
                    emails=[email],
                    tags=["doc_mention", source],
                    source=source,
                    notes=f"Mentioned in document: {title}",
                )
                if r.get("id") and r["id"] not in touched_people:
                    touched_people.append(r["id"])
            for phone in extracted["phones"]:
                r = clawsum_contacts.upsert_person(
                    cur,
                    phones=[phone],
                    tags=["doc_mention", source],
                    source=source,
                    notes=f"Phone in document: {title}",
                )
                if r.get("id") and r["id"] not in touched_people:
                    touched_people.append(r["id"])

            cur.execute(
                """
                INSERT INTO ops.documents (
                  title, source, source_ref, media_id, uri, content_type, sha256, summary, person_ids, meta
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::uuid[],%s::jsonb)
                RETURNING id::text
                """,
                (
                    title[:300],
                    source if source in ("gmail", "call", "chatgpt", "upload", "scrape", "other") else "other",
                    source_ref,
                    media_id,
                    uploaded["uri"],
                    content_type,
                    digest,
                    text[:500],
                    touched_people or None,
                    json.dumps(meta or {}),
                ),
            )
            doc_id = cur.fetchone()["id"]

            for ch in chunk_text(text, size=chunk_size):
                cur.execute(
                    """
                    INSERT INTO ops.document_chunks (document_id, chunk_index, text, char_start, char_end)
                    VALUES (%s::uuid, %s, %s, %s, %s)
                    ON CONFLICT (document_id, chunk_index) DO UPDATE SET text = EXCLUDED.text
                    RETURNING id::text, chunk_index
                    """,
                    (doc_id, ch["chunk_index"], ch["text"], ch["char_start"], ch["char_end"]),
                )
                row = cur.fetchone()
                chunk_rows.append({"id": row["id"], "chunk_index": row["chunk_index"], "text": ch["text"]})

    # Arcade mirror
    try:
        from clawsum_arcade import mirror_document, upsert_vertex, _cmd, _esc

        mirror_document(
            doc_id=doc_id,
            title=title,
            uri=uploaded["uri"],
            summary=text[:500],
            person_ids=touched_people,
        )
        for ch in chunk_rows:
            upsert_vertex(
                "SourceChunk",
                ch["id"],
                {
                    "document_id": doc_id,
                    "chunk_index": ch["chunk_index"],
                    "text": ch["text"][:4000],
                    "title": title,
                },
            )
            try:
                _cmd(
                    f"CREATE EDGE `HasChunk` FROM "
                    f"(SELECT FROM `Document` WHERE clawsum_id = {_esc(doc_id)}) "
                    f"TO (SELECT FROM `SourceChunk` WHERE clawsum_id = {_esc(ch['id'])})"
                )
            except Exception:
                try:
                    _cmd(
                        f"CREATE EDGE `Mentions` FROM "
                        f"(SELECT FROM `Document` WHERE clawsum_id = {_esc(doc_id)}) "
                        f"TO (SELECT FROM `SourceChunk` WHERE clawsum_id = {_esc(ch['id'])})"
                    )
                except Exception:
                    pass
            # Link chunk → people whose email/phone appears in this chunk
            chunk_emails = set(clawsum_contacts.extract_emails(ch["text"]))
            chunk_phones = set(clawsum_contacts.extract_phones(ch["text"]))
            for pid in touched_people:
                try:
                    _cmd(
                        f"CREATE EDGE `Mentions` FROM "
                        f"(SELECT FROM `SourceChunk` WHERE clawsum_id = {_esc(ch['id'])}) "
                        f"TO (SELECT FROM `Person` WHERE clawsum_id = {_esc(pid)})"
                    )
                except Exception:
                    pass
                if not chunk_emails and not chunk_phones:
                    break
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: arcade document mirror failed: {exc}", file=sys.stderr)

    return {
        "document_id": doc_id,
        "uri": uploaded["uri"],
        "chunks": len(chunk_rows),
        "people": touched_people,
        "sha256": digest,
    }


def store_call_recording(
    *,
    wav_path: Path | None = None,
    wav_bytes: bytes | None = None,
    transcript: str,
    title: str | None = None,
    caller_name: str | None = None,
    caller_phone: str | None = None,
    callee_phone: str | None = None,
    started_at: str | None = None,
    duration_seconds: int | None = None,
    source_ref: str | None = None,
) -> dict[str, Any]:
    """Archive .wav + transcript to MinIO clawsum-calls, ETL transcript to Arcade."""
    if not wav_bytes and not wav_path:
        raise ValueError("wav_path or wav_bytes required")
    if wav_path and not wav_bytes:
        wav_bytes = Path(wav_path).read_bytes()
    assert wav_bytes is not None

    env = _env()
    bucket = env.get("MINIO_BUCKET_CALLS", "clawsum-calls")
    day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    ref = source_ref or hashlib.sha256(wav_bytes).hexdigest()[:16]
    audio_key = f"calls/{day}/{ref}.wav"
    tx_key = f"calls/{day}/{ref}.transcript.txt"

    audio_up = minio_store.upload_bytes(
        wav_bytes,
        bucket=bucket,
        object_key=audio_key,
        content_type="audio/wav",
        filename=f"{ref}.wav",
        env=env,
    )
    tx_bytes = (transcript or "").encode("utf-8")
    tx_up = minio_store.upload_bytes(
        tx_bytes,
        bucket=bucket,
        object_key=tx_key,
        content_type="text/plain",
        filename=f"{ref}.transcript.txt",
        env=env,
    )

    conn, factory = _pg()
    caller_id = None
    with conn:
        with conn.cursor(cursor_factory=factory) as cur:
            if caller_phone or caller_name:
                r = clawsum_contacts.upsert_person(
                    cur,
                    display_name=caller_name,
                    phones=[caller_phone] if caller_phone else [],
                    tags=["call_party"],
                    source="call",
                )
                caller_id = r.get("id")
            callee_id = None
            if callee_phone:
                r2 = clawsum_contacts.upsert_person(
                    cur,
                    phones=[callee_phone],
                    tags=["call_party"],
                    source="call",
                )
                callee_id = r2.get("id")

            audio_media = minio_store.record_media(
                cur,
                audio_up,
                source="call",
                source_ref=ref,
                person_id=caller_id,
                meta={"role": "audio"},
            )
            tx_media = minio_store.record_media(
                cur,
                tx_up,
                source="call",
                source_ref=ref,
                person_id=caller_id,
                meta={"role": "transcript"},
            )

    # Document ETL on transcript
    doc = ingest_document(
        title=title or f"Call transcript {ref}",
        text=transcript or "",
        source="call",
        source_ref=ref,
        filename=f"{ref}.transcript.txt",
        content_type="text/plain",
        upload_bytes=tx_bytes,
        person_ids=[p for p in (caller_id, callee_id) if p],
        meta={"audio_uri": audio_up["uri"]},
    )

    with conn:
        with conn.cursor(cursor_factory=factory) as cur:
            cur.execute(
                """
                INSERT INTO ops.call_recordings (
                  title, caller_person_id, callee_person_id, started_at, duration_seconds,
                  audio_media_id, transcript_media_id, document_id, source, source_ref, meta
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'call',%s,%s::jsonb)
                RETURNING id::text
                """,
                (
                    title or f"Call {ref}",
                    caller_id,
                    callee_id,
                    started_at,
                    duration_seconds,
                    audio_media,
                    tx_media,
                    doc["document_id"],
                    ref,
                    json.dumps({"audio_uri": audio_up["uri"], "transcript_uri": tx_up["uri"]}),
                ),
            )
            call_id = cur.fetchone()["id"]

    return {
        "call_id": call_id,
        "audio_uri": audio_up["uri"],
        "transcript_uri": tx_up["uri"],
        "document_id": doc["document_id"],
        "chunks": doc["chunks"],
        "people": doc["people"],
    }


def backfill_media(limit: int = 50) -> int:
    """Chunk existing document/transcript media_objects that lack ops.documents."""
    conn, factory = _pg()
    n = 0
    with conn:
        with conn.cursor(cursor_factory=factory) as cur:
            cur.execute(
                """
                SELECT m.id::text, m.uri, m.filename, m.kind, m.source, m.source_ref, m.content_type
                FROM ops.media_objects m
                LEFT JOIN ops.documents d ON d.media_id = m.id
                WHERE d.id IS NULL
                  AND m.kind IN ('document', 'transcript', 'attachment')
                  AND (m.content_type ILIKE 'text/%%' OR m.filename ILIKE '%%.txt'
                       OR m.filename ILIKE '%%.md' OR m.kind = 'transcript')
                ORDER BY m.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = list(cur.fetchall() or [])
    # Download from MinIO and ingest into Postgres + Arcade
    for row in rows:
        try:
            blob, meta = minio_store.download_uri_bytes(row["uri"], env=_env())
            guessed_type = row.get("content_type") or meta.get("content_type") or "text/plain"
            text = ""
            # Prefer real object bytes for text-ish payloads
            if blob:
                try:
                    text = blob.decode("utf-8", errors="replace")
                except Exception:
                    pass
            if not (text or "").strip():
                print(f"skip backfill empty uri={row['uri']}", file=sys.stderr)
                continue
            out = ingest_document(
                title=row.get("filename") or row.get("source_ref") or "Backfilled document",
                text=text,
                source=row.get("source") or "other",
                source_ref=row.get("source_ref") or row.get("id"),
                filename=row.get("filename") or "backfill.txt",
                content_type=row.get("content_type") or meta.get("content_type") or guessed_type,
                upload_bytes=blob,
                meta={"backfill_media_id": row.get("id"), "backfill_uri": row.get("uri")},
            )
            print(
                f"backfilled uri={row['uri']} document_id={out.get('document_id')}",
                file=sys.stderr,
            )
            n += 1
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: backfill failed uri={row['uri']}: {exc}", file=sys.stderr)
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Clawsum document / call ETL")
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--title", default="")
    ap.add_argument("--source", default="upload")
    ap.add_argument("--source-ref")
    ap.add_argument("--call-wav", help="Path to .wav for call archive")
    ap.add_argument("--call-transcript", help="Transcript text or path to .txt")
    ap.add_argument("--caller-phone")
    ap.add_argument("--caller-name")
    ap.add_argument("--backfill-media", action="store_true")
    args = ap.parse_args()

    if args.backfill_media:
        print({"backfilled": backfill_media()})
        return

    if args.call_wav:
        tx = args.call_transcript or ""
        if tx and Path(tx).is_file():
            tx = Path(tx).read_text(encoding="utf-8", errors="replace")
        out = store_call_recording(
            wav_path=Path(args.call_wav),
            transcript=tx,
            title=args.title or Path(args.call_wav).stem,
            caller_name=args.caller_name,
            caller_phone=args.caller_phone,
            source_ref=args.source_ref,
        )
        print(json.dumps(out, indent=2))
        return

    if args.file:
        path = Path(args.file)
        text, ctype = _read_file_text(path)
        out = ingest_document(
            title=args.title or path.name,
            text=text,
            source=args.source,
            source_ref=args.source_ref or path.name,
            filename=path.name,
            content_type=ctype,
            upload_bytes=path.read_bytes() if ctype != "text/plain" else text.encode("utf-8"),
        )
        print(json.dumps(out, indent=2))
        return

    if args.text:
        out = ingest_document(
            title=args.title or "Untitled note",
            text=args.text,
            source=args.source,
            source_ref=args.source_ref,
        )
        print(json.dumps(out, indent=2))
        return

    ap.error("Provide --text, --file, --call-wav, or --backfill-media")


if __name__ == "__main__":
    main()
