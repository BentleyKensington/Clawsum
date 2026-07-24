---
name: hermes-cockpit-install
description: Installs Clawsum Hermes theme, cockpit plugin, and SOUL proactive instructions. Use when setting up or refreshing the CEO Hermes UI face.
agents: [coding, admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [OPENCLAW_*/Paperclip container access, POSTGRES_*]
approval_actions: []
---

# Hermes cockpit install

```bash
bash /docker/clawsum/scripts/install-hermes-dashboard.sh
bash /docker/clawsum/scripts/install-hermes-cockpit.sh
bash /docker/clawsum/scripts/hermes-dashboard.sh stop || true
bash /docker/clawsum/scripts/hermes-dashboard.sh start
```

Verify SOUL at `/paperclip/.hermes/SOUL.md`. Bind `hermes.${DOMAIN}` via Traefik auth — never expose `:9119` publicly without auth.
