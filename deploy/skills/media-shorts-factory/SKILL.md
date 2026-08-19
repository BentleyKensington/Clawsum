---
name: media-shorts-factory
description: Cuts short-form clips with auto-editor and FFmpeg (crop, captions, NVENC). Optional Cut/Storm UI. Use after media-package-seo hook list exists.
agents: [media]
cells: [media-production, hardware-local-ai]
tier_autonomous: 1
credentials: [FFMPEG_BIN, WHISPER_*, MINIO_*]
approval_actions: []
---

# Media Shorts factory (Phase 2 · Tier 1)

## When to use

Hook timestamps selected (human or LLM); produce 9:16 (and other) draft exports.

## Instructions

1. Prefer **auto-editor** for silence/dead-air cleanup on source when helpful.
2. Drive **FFmpeg** for programmatic cuts:
   - trim/concat by timestamp
   - crop/pad to 9:16 (and 1:1 / 16:9 variants as requested)
   - burn or sidecar captions from Whisper SRT
   - loudnorm + NVENC/QSV when available
3. **Cut/Storm** is optional operator UI — not required for automation.
4. Store drafts in MinIO; attach review links/paths to Paperclip.
5. Stop at **draft**. Publish via `media-publish` + Gerald.

## Escalation

- Cloud clip SaaS (Opus/CapCut) only if local quality fails a deadline → Tier 2 spend + note why.
- Overwriting Boss-approved masters without new issue → forbidden.

## References

- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
