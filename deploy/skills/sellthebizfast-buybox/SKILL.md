---
name: sellthebizfast-buybox
description: Score a business against the SellTheBizFast buy box (Mallien FUEL + Clawsum filters). Pass/maybe/no with reasons.
agents: [sellthebizfast, research, planning]
cells: [sellthebizfast]
tier_autonomous: 1
credentials: [POSTGRES_*]
approval_actions: []
---

# SellTheBizFast buy box

See [SELLTHEBIZFAST.md](../../docs/SELLTHEBIZFAST.md).

## Instructions

1. If BUYBOX.md missing, run `spec-interview` for geo, revenue band, owner-hours max.
2. Score the teaser/listing: years, recession-resistance, owner-dependence, trend, concentration (if known), “job vs asset.”
3. Output: **Pass / Stretch / No** + 5 bullets. Recommend next: NDA+CIM, or pass.
4. Store in Obsidian `SellTheBizFast/deals/<slug>/score.md`. No CIM in Discord.

Cody Sanchez test: would Gerald be buying a job? If owner hours > 40 and no GM, say so.

Billy Batt test: did this come from a hunt system or random broker blast? Still score it the same way.
