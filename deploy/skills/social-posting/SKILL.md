---
name: social-posting
description: Schedule or immediately post ready content-factory packages. Always approval-gated like outbound send.
agents: [social, content, comms, admin]
cells: [media-production]
tier_autonomous: 1
credentials: [YOUTUBE_*, META_*, TIKTOK_*, PAPERCLIP_*, POSTGRES_*]
approval_actions: [social_publish, social_schedule, youtube_upload, youtube_schedule]
---

# Social posting (Tier 2 gate)

## When to use

Idea status `ready` or `queued`; assets exist (video, first frame, thumbnail, caption).

## Instructions

1. Queue if needed:

```bash
python3 /docker/clawsum/scripts/content-factory.py queue --idea-id UUID
# or immediate intent (still needs approval):
python3 /docker/clawsum/scripts/content-factory.py queue --idea-id UUID --now
```

2. Create `ops.approvals` (action `social_publish` or `social_schedule`) with platform, caption, asset paths, schedule time.
3. **Do not post** until Gerald approves — unless a standing Boss rule says a specific evergreen series is pre-approved (log that on the approval row).
4. After approve: YouTube Shorts / Meta / TikTok via approved business APIs only. Otherwise leave ready-to-post package + notify Boss.
5. Write `posted_ref` (URL/id) back to `ops.social_queue`; set idea `posted`.

## Immediate vs schedule

| Boss said | Queue | Post |
|-----------|-------|------|
| “schedule” / silent daily | `scheduled_for` set | after approve |
| “post now” / “ship it” | `--now` | after approve, then post immediately |

## Escalation

OAuth missing → ready-to-post folder + Admin notify. Wipe published content → Tier 3.
