---
name: printful-ops
description: Printful catalog, orders, fulfillment via API. Live product/price changes = Tier 2. Can request Google Photos Picker for mockups.
agents: [printful, shopify, media]
cells: [acceptai-fastbuy, clawsum-platform]
tier_autonomous: 1
credentials: [PRINTFUL_API_TOKEN]
approval_actions: [catalog_mutate, refund]
---

# Printful ops

Docs: https://developers.printful.com/

```env
PRINTFUL_API_TOKEN=
```

```bash
python3 /docker/clawsum/scripts/printful_request.py GET /store/products
python3 /docker/clawsum/scripts/printful_request.py GET /orders
```

## Autonomous

List products, sync status, open orders, shipping estimates. Notes in Obsidian `Printful/`.

## Tier 2

Create/update products, cancel orders, refunds, mockup publish.

**Photos:** `google-photos-picker` — Gerald picks from clawsums@gmail.com; store in MinIO; then attach to Printful file library.

If token missing: report status honestly (lane exists, API not live).
