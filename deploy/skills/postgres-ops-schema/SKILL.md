---
name: postgres-ops-schema
description: Applies and verifies Clawsum ops Postgres schemas (overwatch, email, reminders, archive, CRM). Use when bootstrapping DB or after new migrations.
agents: [coding, data, admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [POSTGRES_*]
approval_actions: [wipe_db]
---

# Postgres ops schema

Order (idempotent where possible):

```text
12-overwatch.sql → 05-ops-email.sql → 06-ops-reminders.sql
→ 13-chatgpt-archive.sql → 14-ops-crm.sql
```

Then seed:

```bash
python3 scripts/seed-business-cells.py
python3 scripts/seed-people-places.py
```

Never drop/wipe without Tier 3 human.
