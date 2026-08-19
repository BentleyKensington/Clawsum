---
name: media-longform-resolve
description: Polishes long-form projects in DaVinci Resolve Studio (scripting/dvr MCP) with FFmpeg deliverables. Use for flagship episodes after Shorts drafts or instead of Shorts-only.
agents: [media]
cells: [media-production, hardware-local-ai]
tier_autonomous: 1
credentials: [RESOLVE_*, FFMPEG_BIN, MINIO_*]
approval_actions: []
---

# Media long-form Resolve (Phase 3 · Tier 1)

## When to use

Flagship podcast/video needs pro timeline, color, Fairlight, or Neural Engine tools.

## Instructions

1. Ensure DaVinci Resolve **Studio** is available on Boss GPU host; prefer `dvr` MCP / Python scripting.
2. Import media + transcript chapters; apply templates (intro/outro, loudness).
3. Optional: Demucs/UVR cleanup before Fairlight.
4. Export masters; use **FFmpeg** for platform-specific derivatives.
5. Attach review package to Paperclip; do not publish.

## Escalation

- Resolve license / Cloud spend → Boss.
- Headless render failures → Coding for host tooling.

## References

- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
