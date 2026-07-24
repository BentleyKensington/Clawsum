---
name: ghl-lead-ops
description: GHL CRM lead qualify, conversation review, and pipeline reads for a single business cell. Use for WNN or instance GHL accounts — never cross-location.
agents: [ghl, admin]
cells: [wnn-client]
tier_autonomous: 1
credentials: [GHL_*, POSTGRES_*]
approval_actions: [send_sms, send_email, bulk_contact_update, campaign_change]
---

# GHL lead ops

## Rules

1. Load only the PIT for **this** location (`GHL_{SLUG}_*` or cell vault).
2. Follow `templates/ghl/WORKFLOWS.md` + `AGENTS.md` (read/write tools only for Telegram GHL agents).
3. Drafts OK (Tier 1). **Sends** require approval Tier 2.
4. Never query another GHL location’s database.

## Re-engage

Primary path: read `REENGAGE.md` at workspace root (exact path). Landline → tag `landline` after Boss approval.
