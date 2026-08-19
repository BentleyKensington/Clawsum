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

- Prefer `clawsum_contacts.upsert_person` / `upsert_from_email_headers` (merge emails/phones/tags).
- Auto-created Gmail people get `auto_from_gmail` / `auto_from_gmail` tags — provisional until Boss confirms.
- ArcadeDB `Person` vertices + edges are mirrored best-effort (graph recall); Postgres stays SoR.
- Attachments land in MinIO (`clawsum-attachments`) + `ops.media_objects`.
- Confirm Boss / client orgs before GHL writes.
- Personal emails stay on `personal-admin` unless re-scoped.

```bash
# Shared upsert (also used by gmail-sync)
python3 -c "from clawsum_contacts import upsert_person; ..."
```
