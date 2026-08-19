---
name: content-repurpose
description: Cuts a long-form asset into extra shorts/posts for the content factory. Use after a master video or transcript exists.
agents: [content, media]
cells: [media-production]
tier_autonomous: 1
credentials: [MINIO_*, PAPERCLIP_*, FFMPEG_BIN]
approval_actions: []
---

# Content repurpose (Tier 1)

## Instructions

1. Source a master (`ops.media_objects` or content-factory video).
2. Open child `ops.content_ideas` (`source=agent`) with evergreen=true when the cut still works next year.
3. Hand cuts to `media-shorts-factory`; packs to `content-pack`.
4. Publish only via `social-posting` (Tier 2).
