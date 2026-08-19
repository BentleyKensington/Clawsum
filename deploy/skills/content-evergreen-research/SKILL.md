---
name: content-evergreen-research
description: Turns a seed (Boss or daily bank) into a clever evergreen angle using trend signals that will still work next year. Does not publish.
agents: [research, content, hermes, media]
cells: [media-production]
tier_autonomous: 1
credentials: [POSTGRES_*, PAPERCLIP_*, LLM optional]
approval_actions: []
---

# Content evergreen research (Tier 1)

## When to use

Inbox idea exists, or daily factory needs angles. Pair with `media-trends-brief` for format signals.

## Instructions

1. Read `ops.content_ideas` row (or Paperclip description).
2. Prefer **evergreen**: principles, systems, repeatable plays — not yesterday’s headline.
3. You may *borrow a format* from trends (hook length, on-screen style) without dating the claim.
4. Write `angle` + 3 clever variants on the Paperclip issue.
5. Hand off to `content-pack` (`content-factory.py pack --idea-id …`).

## Escalation

Paid trend APIs → Data + Boss. Auto-post from research → forbidden.
