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

1. Read `$ACCEPTAI_CODEBASE_PATH` (default **`C:\APPS\Projects\AcceptAI`**). Ignore the stale root README “minimal scaffold.” Required reading: `aaip_service/app/main.py` (AAIP FastAPI: catalog feeds, ACP, OAuth, Stripe, AI browse), `aaip-mcp-server/README.md` (agent shopping MCP), `shopify-marketplace-app/acceptai-marketplace/` (Shopify app). FastBuy copy stays on `commerce-fastbuy`.
2. SSH via `product-ssh-ops` when `$ACCEPTAI_SSH_HOST` is set, or call `$ACCEPTAI_API_BASE` with `ACCEPTAI_API_KEY` (header never printed). If SSH host is empty, ask once — do not guess Vocalitic’s box.
3. Dashboard + logs → observations in Obsidian `AcceptAI/` → Paperclip with recommended diffs. Comms drafts customer copy separately.
4. Pricing, live offer, refunds, prod deploy = Tier 2.

## Escalation

No codebase path → ask. Do not mix SellTheBizFast CIMs into this cell.
