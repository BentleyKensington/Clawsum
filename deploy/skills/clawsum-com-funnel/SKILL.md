---
name: clawsum-com-funnel
description: Updates and deploys clawsum.com marketing funnel, Founding Operator offer, logos, and SEO assets. Use for site copy, pricing, or marketing publish.
agents: [coding, comms, admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [SSH/VPS, optional PORKBUN_*]
approval_actions: [pricing_change, dns_change]
---

# clawsum.com funnel

- Source: `deploy/sites/clawsum-com/`
- Offer: `/offer/` — $10,000 year in full (save $1,964) or $997/mo
- Deploy: sync to `/docker/clawsum/sites` + `data/sites`; restart `clawsum-marketing`
- Pricing/legal copy changes → Boss confirm (Tier 2 if public pricing shift)
