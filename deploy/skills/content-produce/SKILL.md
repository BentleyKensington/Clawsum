---
name: content-produce
description: Renders flyer card, first-frame, thumbnail, and draft Shorts video from a content pack. Use after content-pack.
agents: [media, content]
cells: [media-production, hardware-local-ai]
tier_autonomous: 1
credentials: [FFMPEG_BIN, MINIO_*, POSTGRES_*]
approval_actions: []
---

# Content produce (Tier 1 · draft only)

## When to use

Pack exists; need visual + video drafts for Social review.

## Instructions

```bash
python3 /docker/clawsum/scripts/content-factory.py produce --idea-id UUID
```

Writes:

- `flyer.png` (4:5)
- `thumbnail.png` (16:9)
- `first-frame.png` (9:16)
- `draft-short.mp4` (9:16, ~8s title-card draft)

Upgrade path: replace cards with Comfy/Flux stills + ElevenLabs VO + FFmpeg concat (`media-shorts-factory` / `media-generative-broll`). Still **draft** until `social-posting` + approval.

## Escalation

Paid GPU / cloud render = Tier 2. Overwrite approved masters = forbidden.
