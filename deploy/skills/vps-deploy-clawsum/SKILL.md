---
name: vps-deploy-clawsum
description: Deploys Clawsum platform updates to the reference VPS — git sync, site publish, schema apply, cockpit install. Use when shipping code or marketing to production.
agents: [coding, admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [OPENCLAW_*, POSTGRES_*, BOSS_OPS_*, SSH host access]
approval_actions: [production_deploy, dns_change, credential_rotate]
---

# VPS deploy Clawsum

## Safe sequence

1. Diff locally; commit only when Boss asked.
2. Sync `deploy/` → `/docker/clawsum` (SCP or pull if git-backed).
3. Apply SQL migrations explicitly (`postgres-init/1x-*.sql`).
4. Marketing: copy `sites/clawsum-com` → `data/sites/clawsum-com`; `docker restart clawsum-marketing`.
5. Cockpit: `bash scripts/install-hermes-cockpit.sh` then restart dashboard.
6. Smoke: curl apex, offer, hermes health.

## Do not

- Force-push main, wipe DB, or rotate creds without Tier 2–3 human.
- Run full `setup-clawsum-domains.sh` blindly (may regenerate ops auth).
