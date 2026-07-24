---
name: gmail-inbox-review
description: Reviews every clawsums@gmail.com message with per-email analysis, cell/person linking, local tasks, and Boss questions. Use for inbox review, email triage reports, or CRM from mail.
agents: [admin, hermes, data]
cells: [clawsum-platform, personal-admin]
tier_autonomous: 1
credentials: [GMAIL_*, POSTGRES_*, PAPERCLIP_COMPANY_ID]
approval_actions: [send_email]
---

# Gmail inbox review

## Instructions

1. Ensure schema `05-ops-email.sql` + `14-ops-crm.sql` applied.
2. Sync then review:

```bash
python3 /docker/clawsum/scripts/gmail-sync.py
python3 /docker/clawsum/scripts/gmail-inbox-review.py --inbox-only --all --markdown --create-reminders
```

3. Each email must have `analysis_report` + `ops.email_reviews` row.
4. Action items → `ops.tasks`; optional Paperclip via `gmail-triage.py`.
5. **Do not send** mail in this skill (Tier 2).

## Output

Markdown with per-email sections, or cockpit Inbox tab.
