---
name: people-places-crm
description: Seeds and maintains ops.people, ops.places, and person_places linked to business cells. Use when onboarding contacts from email or mapping offices/regions.
agents: [admin, data]
cells: ["*"]
tier_autonomous: 1
credentials: [POSTGRES_*]
approval_actions: []
---

# People & places CRM

```bash
python3 /docker/clawsum/scripts/seed-business-cells.py
python3 /docker/clawsum/scripts/seed-people-places.py
bash /docker/clawsum/scripts/run-overwatch-crm.sh
```

## Rules

- Auto-created Gmail people are provisional (`auto_from_gmail` tag).
- Confirm Boss / client orgs before GHL writes.
- Personal emails stay on `personal-admin` unless re-scoped.
