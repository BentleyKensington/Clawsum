---
name: personal-admin
description: Handles Gerald personal-admin cell work — calendar summaries, personal inbox flags, private reminders — never mixed into client CRM agents.
agents: [admin, hermes]
cells: [personal-admin]
tier_autonomous: 1
credentials: [GMAIL_*, POSTGRES_*, calendar if configured]
approval_actions: [send_email, send_text, calendar_invite]
---

# Personal admin

- Keep outputs in personal-admin namespace.
- Draft calendar invites / personal replies → Tier 2 to send.
- Banking/legal/payroll = never autonomous.
