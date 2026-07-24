---
name: commerce-fastbuy
description: Summarizes AcceptAI / FastBuy funnel and draft customer communications. Use for commerce cell reporting — not bulk refunds.
agents: [comms, planning, admin]
cells: [acceptai-fastbuy]
tier_autonomous: 1
credentials: [POSTGRES_*]
approval_actions: [customer_comms, pricing_change, paid_ads, refunds_bulk]
---

# Commerce / FastBuy

- Tier 0–1: revenue/issue summaries, draft copy.
- Pricing, ads, bulk refunds, payouts → approval / never autonomous per cell profile.
