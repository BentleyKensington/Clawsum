---
name: hermes-proactive-drive
description: Instructs Hermes to read Paperclip tasks, link archive/inbox items, infer intent, and ask one sharp clarifying question per stuck item. Use for JARVIS proactive sessions.
agents: [hermes, admin]
cells: [clawsum-platform, personal-admin]
tier_autonomous: 1
credentials: [PAPERCLIP_*, POSTGRES_*]
approval_actions: [create_issue_bulk]
---

# Hermes proactive drive

## Instructions

1. Load SOUL: `examples/hermes-cockpit/SOUL.md`.
2. Read Paperclip board first (truth).
3. Pull drive-forward archive + inbox:

```bash
python3 /docker/clawsum/scripts/archive-proactive-brief.py --markdown
python3 /docker/clawsum/scripts/gmail-inbox-review.py --inbox-only --markdown --no-per-email-report
```

4. Cross-link related items (say `CLA-…` ids).
5. Ask **one** question per blocked/needs_boss item.
6. Propose Paperclip updates; do not stealth-execute Tier 2+.
7. Keep `scope=personal` out of business agents.

## Escalation

Long autonomous runs require `Boss authorized Hermes: yes` on the issue.
