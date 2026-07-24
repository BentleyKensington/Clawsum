---
name: roofing-storm-intel
description: Summarizes storm / hail / lead signals for Roofing OS / CEOroof cell. Use for storm briefings and outreach draft prep.
agents: [realestate, research, admin]
cells: [roofing-os]
tier_autonomous: 1
credentials: [POSTGRES_*, GHL_*]
approval_actions: [send_outreach, paid_data_order]
---

# Roofing storm intel

1. Gather storm/lead summaries available to the cell (DB / CRM reads).
2. Produce CEO-ready brief: geography, urgency, recommended next actions.
3. Outreach drafts OK; **send** = Tier 2 approval.
4. No legal/insurance claim filings autonomous.
