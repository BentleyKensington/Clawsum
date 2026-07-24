---
name: skill-template
description: Template for new Clawsum platform skills. Copy this folder when adding a skill; do not invoke as a runtime skill.
agents: []
cells: []
tier_autonomous: 0
credentials: []
approval_actions: []
disable-model-invocation: true
---

# Skill title

## When to use

One sentence trigger.

## Instructions

1. …
2. …

## Scripts (optional)

```bash
python3 /docker/clawsum/scripts/example.py
```

## Escalation

- Tier 2+ → create `ops.approvals` via `overwatch-create-approval.py` before acting.
- Unclear cell → ask Boss; do not guess across businesses.

## References

- [AUTHORITY.md](../AUTHORITY.md)
- Related docs under `deploy/docs/`
