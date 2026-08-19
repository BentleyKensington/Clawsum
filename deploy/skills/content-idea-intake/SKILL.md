---
name: content-idea-intake
description: Capture a Boss or Hermes idea into the evergreen content factory. Use when Gerald sends a topic, hook, or "make content about…".
agents: [hermes, content, research, admin]
cells: [media-production, clawsum-platform]
tier_autonomous: 1
credentials: [POSTGRES_*, PAPERCLIP_*]
approval_actions: []
---

# Content idea intake (Tier 1)

## When to use

Gerald pastes an idea in Boss/Hermes/Discord: “make a post about…”, “evergreen on…”, “flyer + video for…”.

## Instructions

1. Ack. Confirm evergreen unless he said it is time-bound news.
2. File the seed:

```bash
python3 /docker/clawsum/scripts/content-factory.py intake --text "…" --source boss
```

3. Open/update a Paperclip issue, cell `media-production`:
   - Research step → **Clawsum Research**
   - Pack (topic, flyer, images, story, script) → **Clawsum Content**
   - Produce video / first frame / thumbnail → **Clawsum Media**
   - Schedule or post → **Clawsum Social** (Tier 2)
4. Do **not** publish from this skill.

## Escalation

Time-sensitive news that must expire → `--not-evergreen` and say so on the issue.
