---
name: ghl-reengage
description: Summarizes and executes re-engage lists from REENGAGE.md for GHL contacts. Use when Boss asks for re-engage summary or follow-up batch.
agents: [ghl, admin]
cells: [wnn-client]
tier_autonomous: 1
credentials: [GHL_*]
approval_actions: [send_sms, send_email]
---

# GHL re-engage

1. `read REENGAGE.md` (or `notes/REENGAGE.md`) — do not search/glob if Telegram GHL constraints apply.
2. Summarize cohorts for Boss.
3. Skip **Move on / landline** for SMS; propose `landline` tag with approval.
4. Batch sends → create Tier 2 approval first.
