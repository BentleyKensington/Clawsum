---
name: cell-isolation-check
description: Verifies business cell boundaries — credentials, memory namespaces, and cross-cell leakage. Use before enabling a cell agent or after adding a new business.
agents: [admin, coding, planning]
cells: ["*"]
tier_autonomous: 0
credentials: [POSTGRES_*]
approval_actions: []
---

# Cell isolation check

## Checklist

- [ ] Row exists in `ops.businesses` with correct `slug` / `memory_namespace`
- [ ] `allowed_actions` / `approval_required` / `never_autonomous` populated
- [ ] Credentials for this cell only in vault (no shared PIT across cells)
- [ ] Paperclip agent mapped in `ops.overwatch_agents` (when used)
- [ ] No other cell’s secrets in this agent’s env
- [ ] Personal-admin not mixed into client CRM tools

```bash
python3 /docker/clawsum/scripts/seed-business-cells.py --list
```
