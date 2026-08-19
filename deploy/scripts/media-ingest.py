#!/usr/bin/env python3
"""Phase 0 media ingest stub — watch folders / URL list → MinIO + Postgres metadata.

Requires: yt-dlp, ffmpeg/ffprobe, MINIO_*, POSTGRES_*.
Safe to run dry-run without credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha256_file(path: Path, limit: int = 0) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        if limit:
            h.update(f.read(limit))
        else:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def ffprobe(path: Path) -> dict:
    cmd = [
        os.environ.get("FFPROBE_BIN", "ffprobe"),
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return json.loads(out)
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Clawsum media ingest (Phase 0 stub)")
    ap.add_argument("--watch", type=Path, help="Local folder to scan")
    ap.add_argument("--urls-file", type=Path, help="File with one URL per line")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true", help="Actually download/upload (disables dry-run)")
    args = ap.parse_args()
    dry = not args.apply

    items: list[dict] = []
    if args.watch and args.watch.is_dir():
        for p in sorted(args.watch.rglob("*")):
            if p.is_file() and p.suffix.lower() in {
                ".mp4",
                ".mov",
                ".mkv",
                ".webm",
                ".mp3",
                ".wav",
                ".m4a",
                ".aac",
            }:
                items.append(
                    {
                        "source": "watch",
                        "path": str(p),
                        "sha256": sha256_file(p, limit=8 * 1024 * 1024),
                        "probe": ffprobe(p),
                    }
                )
    if args.urls_file and args.urls_file.is_file():
        for line in args.urls_file.read_text().splitlines():
            url = line.strip()
            if url and not url.startswith("#"):
                items.append({"source": "url", "url": url, "note": "yt-dlp fetch on --apply"})

    report = {
        "dry_run": dry,
        "count": len(items),
        "ffmpeg": os.environ.get("FFMPEG_BIN", "ffmpeg"),
        "paperclip_api": os.environ.get("PAPERCLIP_API_URL")
        or os.environ.get("PAPERCLIP_API"),
        "items": items,
    }
    print(json.dumps(report, indent=2)[:20000])
    if dry:
        print(
            "\nDry-run only. Re-run with --apply after MinIO/Postgres env and yt-dlp are ready.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
