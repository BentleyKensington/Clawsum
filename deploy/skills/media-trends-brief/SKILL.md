---
name: media-trends-brief
description: Researches niche video/audio trends and formats for social + AEO/GEO visibility. Use when Boss or Hermes wants trend signals without auto-publishing.
agents: [media, research, hermes]
cells: [media-production]
tier_autonomous: 0
credentials: [LLM optional]
approval_actions: []
---

# Media trends brief (Tier 0)

## When to use

Detect new formats, hooks, or niche trends that should feed the production queue.

## Instructions

1. Scan allowed sources (YouTube niche SERP, RSS, competitor channels via public pages / yt-dlp metadata — respect ToS).
2. Summarize 5–10 opportunities: format, hook pattern, estimated effort, SEO/AEO angle.
3. Open or update Paperclip issues for **Clawsum Media** — do **not** download/publish from this skill alone.
4. Hand heavy research synthesis to `research-brief` when needed.

## Escalation

- Paid trend APIs / scrapers → coordinate with **data** + Boss.
- Auto-publish from trends → forbidden (use `media-publish` + Tier 2).

## References

- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
- [AUTHORITY.md](../AUTHORITY.md)
