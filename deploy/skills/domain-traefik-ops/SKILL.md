---
name: domain-traefik-ops
description: Manages clawsum.com DNS map and Traefik routes for marketing and ops hosts. Use for subdomain setup, auth wall, or marketing publish routing.
agents: [coding, admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [PORKBUN_*, BOSS_OPS_*, TRAEFIK access]
approval_actions: [dns_change, production_deploy]
---

# Domain / Traefik ops

- Map: `deploy/docs/DOMAIN-MAP.md`
- Prefer targeted updates over full auth regen.
- Marketing public; ops hosts basic-auth.
- Hermes may need host-rewrite middleware.
- Rotate Porkbun keys if ever pasted in chat.
