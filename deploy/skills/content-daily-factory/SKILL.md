---
name: content-daily-factory
description: Daily evergreen production — seed one idea, pack, produce, queue for Social. Use for the morning factory cron or "run today's content".
agents: [content, media, research, social, hermes]
cells: [media-production]
tier_autonomous: 1
credentials: [POSTGRES_*, PAPERCLIP_*, FFMPEG_BIN]
approval_actions: []
---

# Daily evergreen factory (Tier 1 through queue)

## Cadence

America/Chicago **07:10** seed · **07:20** `run-one` (cron `clawsum-content-factory`).

Boss ideas in `inbox` take priority over the evergreen bank.

## Instructions

```bash
python3 /docker/clawsum/scripts/content-factory.py daily --count 1
python3 /docker/clawsum/scripts/content-factory.py run-one
```

`run-one` = pack → produce → social queue (`pending_approval`). **Does not post.**

## Escalation

Post/schedule live → `social-posting` + Gerald (Tier 2), or Boss said **post now** *and* approval exists.
