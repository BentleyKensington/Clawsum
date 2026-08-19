---
name: acceptai-product-ops
description: Operate AcceptAI / FastBuy as a product — codebase + SSH/API; recommend changes for approval. Not bulk ads or refunds.
agents: [acceptai, coding, comms]
cells: [acceptai-fastbuy]
tier_autonomous: 1
credentials: [ACCEPTAI_SSH_*, ACCEPTAI_API_*, ACCEPTAI_CODEBASE_PATH]
approval_actions: [production_deploy, pricing_change, customer_comms]
---

# AcceptAI product ops

See [PRODUCT-AGENTS.md](../../docs/PRODUCT-AGENTS.md). Same discipline as Vocalitic.

## Instructions

1. Read `$ACCEPTAI_CODEBASE_PATH` (README, app purpose, admin/API).
2. SSH via `product-ssh-ops` or call `$ACCEPTAI_API_BASE` with `ACCEPTAI_API_KEY` (header never printed).
3. Dashboard + logs → observations → Paperclip. Comms drafts customer copy separately (`commerce-fastbuy`).
4. Pricing, live offer, refunds, prod deploy = Tier 2.

## Escalation

No codebase path → ask. Do not mix SellTheBizFast CIMs into this cell.
