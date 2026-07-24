---
name: overwatch-approvals
description: Create and decide risk-tiered ops.approvals for governed actions. Use when an agent needs Gerald approval before send, deploy, spend, or credential change.
agents: [admin, paperclip, hermes]
cells: ["*"]
tier_autonomous: 0
credentials: [POSTGRES_*]
approval_actions: [approve, reject, revise]
---

# Overwatch approvals

## Create

```bash
python3 /docker/clawsum/scripts/overwatch-create-approval.py \
  --business wnn-client \
  --action-type send_sms \
  --summary "Re-engage 12 warm leads" \
  --risk-level tier_2
```

## Decide (Boss / Admin only as Gerald proxy when authorized)

```bash
python3 /docker/clawsum/scripts/overwatch-decide-approval.py \
  --id UUID --decision approve --note "OK send"
```

## Rules

- Tier 2–3 actions **blocked** until `status=approved`.
- Log via `ops.audit_logs`.
- Cockpit: Approvals tab / `/api/plugins/clawsum-cockpit/approvals`.
