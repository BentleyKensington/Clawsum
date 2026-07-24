---
name: reminders-boss-nudge
description: Manages ops.reminders and sends daily Telegram nudges until done or snoozed. Use for Boss follow-ups tied to email or tasks.
agents: [admin]
cells: [clawsum-platform, personal-admin]
tier_autonomous: 1
credentials: [POSTGRES_*, TELEGRAM_*]
approval_actions: []
---

# Reminders / Boss nudge

```bash
python3 /docker/clawsum/scripts/reminders-notify.py
```

SQL patterns:

```sql
UPDATE ops.reminders SET snoozed_until = CURRENT_DATE + 3 WHERE id = N;
UPDATE ops.reminders SET completed_at = now() WHERE id = N;
```

Link `business_id` / `person_id` / `task_id` / `gmail_id` when creating rows.
