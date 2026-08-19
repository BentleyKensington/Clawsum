---
name: media-package-seo
description: Builds chapters, titles, descriptions, tags, FAQ/schema, show notes, and social copy packs from transcripts for SEO/AEO/GEO. Use after transcription.
agents: [media, research, hermes]
cells: [media-production]
tier_autonomous: 1
credentials: [POSTGRES_*, PAPERCLIP_*, LLM optional]
approval_actions: []
---

# Media package SEO / AEO / GEO (Phase 1 · Tier 1)

## When to use

Transcript ready; need long-form metadata + multi-surface copy before cuts or publish.

## Instructions

1. Load transcript + media metadata.
2. LLM package (store as draft artifact on the Paperclip issue / Postgres JSON):
   - Titles (3–5 variants), description, tags, chapters with timestamps
   - FAQ / answer-style blocks for AEO/GEO
   - Show notes, blog outline, newsletter blurb
   - LinkedIn / X / IG / FB copy variants
   - Hook list (timestamped) for Shorts scoring
3. Hermes may **propose** packages; OpenClaw **media** owns durable writes.
4. Do **not** publish. Hand render work to `media-shorts-factory` / `media-longform-resolve`.

## Escalation

- Publishing metadata live on YouTube = `media-publish` (Tier 2).
- Brand-sensitive claims → Boss review note on issue.

## References

- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
