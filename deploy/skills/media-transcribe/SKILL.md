---
name: media-transcribe
description: Transcribes ingested media with Faster Whisper, writing word-level timestamps and searchable text. Use after media-ingest-watch.
agents: [media]
cells: [media-production, hardware-local-ai]
tier_autonomous: 1
credentials: [WHISPER_*, MINIO_*, POSTGRES_*]
approval_actions: []
---

# Media transcribe (Phase 0 · Tier 1)

## When to use

New media_object rows without transcripts, or Boss asks to re-transcribe.

## Instructions

1. Pull audio/video from MinIO (or local cache).
2. Run **Faster Whisper** (`WHISPER_*` endpoint or local CUDA). Prefer `large-v3` / `distil-large-v3` when VRAM free; otherwise queue behind chat (see `hardware-local-ai`).
3. Persist: full text, SRT/VTT, word timestamps JSON, language, model id.
4. Link transcript to `ops.media_objects` / transcript table.
5. Open follow-up Paperclip for `media-package-seo` when transcript quality is OK.

## Escalation

- Cloud Whisper API spend without local fallback → Tier 2.
- Do not overwrite human-edited captions without note.

## References

- [LOCAL-STACK-PLAN.md](../../docs/LOCAL-STACK-PLAN.md)
- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
