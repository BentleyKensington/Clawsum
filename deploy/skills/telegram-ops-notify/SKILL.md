---
name: telegram-ops-notify
description: Sends operator notifications to Telegram (daily brief, reminders, alerts) without leaking secrets. Use for CS Ops / Boss DM delivery.
agents: [admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [TELEGRAM_*]
approval_actions: []
---

# Telegram ops notify

- Use configured bot + `TELEGRAM_REPORT_CHAT_ID` / group ids.
- Strip tokens, PITs, passwords from messages.
- Prefer summaries + deep links to Boss/Hermes.
