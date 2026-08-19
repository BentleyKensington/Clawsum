---
name: content-pack
description: Builds the full creative pack — topic, flyer copy, image prompts, social story, production script, SEO titles. Use after research.
agents: [content, research, media, hermes]
cells: [media-production]
tier_autonomous: 1
credentials: [POSTGRES_*, PAPERCLIP_*]
approval_actions: []
---

# Content pack (Tier 1)

## When to use

Idea is inbox/researching; need durable artifacts before render.

## Instructions

```bash
python3 /docker/clawsum/scripts/content-factory.py pack --idea-id UUID
```

Produces under `/docker/clawsum/data/media/exports/content/<id>/`:

| File | Use |
|------|-----|
| `pack.json` | Full pack |
| `flyer.txt` | Flyer copy |
| `story.txt` | Social caption / story |
| `script.txt` | Production VO + on-screen beats |

Image **prompts** (flyer, support stills, thumbnail) live in `pack.json` for Comfy/Flux later. FFmpeg title-cards ship in `content-produce` if no GPU image model.

## Escalation

Brand-sensitive claims → note on issue. Do not post.
