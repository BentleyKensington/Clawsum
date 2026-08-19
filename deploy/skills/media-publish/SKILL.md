---
name: media-publish
description: Publishes or schedules ready media packages to YouTube (and other platforms when APIs approved). Always approval-gated like outbound send.
agents: [media, admin]
cells: [media-production]
tier_autonomous: 1
credentials: [YOUTUBE_*, PAPERCLIP_*, POSTGRES_*]
approval_actions: [youtube_upload, youtube_schedule, social_publish, paid_boost]
---

# Media publish (Tier 2 gate)

## When to use

Draft renders + SEO pack approved; Boss wants upload/schedule.

## Instructions

1. Verify Paperclip acceptance criteria met (file paths, titles, captions, thumbnails).
2. Create `ops.approvals` with full metadata + destination + privacy/schedule.
3. **Do not upload** until Gerald approves.
4. After approve: YouTube Data API `videos.insert` (resumable). Shorts = 9:16 + short duration + `#Shorts` signal as needed.
5. Respect quota (~1600 units/upload). Batch/schedule; request quota increase via Coding if needed.
6. Meta/TikTok: only via approved business APIs; otherwise leave “ready-to-post” package for human paste.
7. Record published IDs/URLs back to Postgres + Paperclip.

## Escalation

- Quota exhaustion / OAuth rotate → Coding + Tier 2/3 as appropriate.
- Wipe channel content → Tier 3 human only.

## References

- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
- [overwatch-approvals](../overwatch-approvals/SKILL.md)
