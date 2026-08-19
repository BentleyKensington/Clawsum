---
name: media-ingest-watch
description: Detects and ingests new local folders, NAS drops, and webhosted video/audio URLs into MinIO with Postgres index. Use for Media Phase 0 intake.
agents: [media, coding]
cells: [media-production, hardware-local-ai]
tier_autonomous: 1
credentials: [MINIO_*, POSTGRES_*, YTDLP_*, FFMPEG_BIN]
approval_actions: []
---

# Media ingest watch (Phase 0 · Tier 1)

## When to use

New recordings, URL drops, or watch-folder events for the media-production cell.

## Instructions

1. Confirm cell `media-production` and watch paths / URL list from the Paperclip issue.
2. Fetch URLs with **yt-dlp**; probe local files with **FFprobe** (`FFMPEG_BIN` sibling).
3. Content-hash dedupe; skip duplicates already in Postgres/MinIO.
4. Store blobs in MinIO (`clawsum-media` or cell bucket); record `ops.media_objects` (+ provenance URL, hash, duration, codec).
5. Notify Admin/Discord that assets are ready for `media-transcribe`.
6. **Google Photos:** do not attempt full-library sync. Accept human Picker selections or local mirror folders only.

## Scripts (planned)

```bash
# Preferred once implemented:
python3 /docker/clawsum/scripts/media-ingest.py --watch /media/inbox --urls-file /tmp/urls.txt
```

Until the script ships: document each ingest in the Paperclip issue and use yt-dlp / FFprobe manually via OpenClaw `exec` on the Boss GPU host.

## Escalation

- Deleting MinIO objects = Tier 2+.
- Cross-cell media (client footage) → Boss re-scope logged.

## References

- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
- [minio-archive-store](../minio-archive-store/SKILL.md)
