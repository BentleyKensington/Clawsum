---
name: ceo-daily-brief
description: Builds the CEO morning brief from Paperclip, approvals, inbox heat, and reminders. Use when Boss asks for daily brief, 7am report context, or overwatch priorities.
agents: [admin, hermes, paperclip]
cells: [clawsum-platform]
tier_autonomous: 0
credentials: [PAPERCLIP_*, POSTGRES_*, TELEGRAM_*]
approval_actions: []
---

# CEO daily brief

## Instructions

1. Pull Paperclip open/blocked/in_progress counts (`PAPERCLIP_API` + company id).
2. Count `ops.approvals` where `status=pending`.
3. Summarize inbox: `ops.emails` pending / needs_boss / last 24h (mailbox `clawsums@gmail.com`).
4. List active `ops.reminders` (not snoozed).
5. Output ≤5 priorities + one clarifying question each for blocked items.
6. Deliver via daily report script or Hermes chat — **no secrets**.

```bash
python3 /docker/clawsum/scripts/daily-global-report.py
# cockpit: GET /api/plugins/clawsum-cockpit/brief
```

## Escalation

Do not enable heartbeats. Point to RESUME-POLICY / CLA-41 if agents are paused.
