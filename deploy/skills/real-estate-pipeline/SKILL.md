---
name: real-estate-pipeline
description: Reviews owned real-estate acquisition pipeline, comps, and draft outreach — non-WNN cell. Use for deal status and research briefs.
agents: [realestate, research, admin]
cells: [real-estate]
tier_autonomous: 1
credentials: [POSTGRES_*, ARCADEDB_*]
approval_actions: [send_outreach, offers, contracts]
---

# Real estate pipeline

- Read deals/comps from cell stores.
- Draft outreach / research briefs (Tier 1).
- Offers, contracts, wire = Tier 2–3 human.
