---
name: shopify-ops
description: Shopify Admin API — products, orders, inventory. Theme/payments/shipping = Tier 2.
agents: [shopify, printful, acceptai]
cells: [acceptai-fastbuy]
tier_autonomous: 1
credentials: [SHOPIFY_STORE, SHOPIFY_ADMIN_TOKEN]
approval_actions: [storefront_publish, payments_change]
---

# Shopify ops

```env
SHOPIFY_STORE=example.myshopify.com
SHOPIFY_ADMIN_TOKEN=
SHOPIFY_API_VERSION=2026-07
```

```bash
python3 /docker/clawsum/scripts/shopify_request.py GET products.json?limit=10
```

## Autonomous

Read products, orders, inventory, abandoned checkouts summary (no full PII in Discord).

## Tier 2

Publish theme, change shipping/payments, bulk price, delete products.

Coordinate Printful sync issues with `printful-ops`. PDP images via `google-photos-picker`.
