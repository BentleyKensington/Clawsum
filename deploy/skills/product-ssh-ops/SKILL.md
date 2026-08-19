---
name: product-ssh-ops
description: SSH to a product host (Vocalitic v1m12, AcceptAI) for read-only inspect. Recommend changes; do not apply without Tier 2.
agents: [vocalitic, acceptai, coding, rocco]
cells: [vocalitic, acceptai-fastbuy, hardware-local-ai]
tier_autonomous: 0
credentials: [VOCALITIC_SSH_*, ACCEPTAI_SSH_*]
approval_actions: [production_deploy, restart_noncritical]
---

# Product SSH ops

## When to use

Need host truth (docker ps, journal, nginx, app logs) for Vocalitic or AcceptAI.

## Instructions

1. Pick env prefix: `VOCALITIC_SSH_*` or `ACCEPTAI_SSH_*`.
2. Connect (do not echo the key):

```bash
# pattern — values from env, never pasted into Discord
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
  -i "$SSH_KEY_PATH" -p "${SSH_PORT:-22}" \
  "${SSH_USER}@${SSH_HOST}" 'hostname; uptime; docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head'
```

3. Allowed read-only: `docker ps`, `systemctl is-active`, tail logs with grep -v for token/password lines, curl local health.
4. Denied without Tier 2: `docker compose up`, restarts, image pulls, nginx reload, DB migrate, `rm`.
5. Write findings + recommended commands in Paperclip. Gerald approves; Coding or the product agent applies.

## Escalation

Auth failure → Boss (key/path). Unexpected host → stop (wrong box).
