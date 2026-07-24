---
name: gmail-sync-triage
description: Syncs Gmail API into ops.emails and classifies pending messages into Paperclip tasks by domain. Use for cron repair, backfill, or triage backlog.
agents: [admin, data]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [GMAIL_*, POSTGRES_*, PAPERCLIP_*, OPENAI_API_KEY]
approval_actions: []
---

# Gmail sync + triage

```bash
python3 /docker/clawsum/scripts/gmail-sync.py --backfill
python3 /docker/clawsum/scripts/gmail-triage.py --limit 20
python3 /docker/clawsum/scripts/gmail-triage.py --dry-run --limit 10
```

- Readonly OAuth only for sync.
- Triage may create Paperclip todos (Tier 1).
- LLM optional (`GMAIL_TRIAGE_MODEL`); rules work offline.
- Docs: `deploy/docs/GMAIL-ADMIN-SETUP.md`
