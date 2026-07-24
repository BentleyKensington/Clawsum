---
name: resume-policy-gate
description: Enforces Boss-paused agent resume rules after CLA-41. Use before enabling heartbeats or unpausing OpenClaw/Paperclip work.
agents: [admin, paperclip, coding]
cells: [clawsum-platform]
tier_autonomous: 0
credentials: [PAPERCLIP_*]
approval_actions: [enable_heartbeats]
---

# Resume policy gate

## Instructions

1. Read `deploy/docs/RESUME-POLICY.md`.
2. Confirm CLA-41 clarifications answered.
3. Park unclear work in `backlog`.
4. Resume **1–2** tasks only, then consider `--enable-heartbeats`.
5. Never urge full fleet unpause from Hermes chat alone.

```bash
python3 /docker/clawsum/scripts/paperclip-resume-work.py   # only after policy met
python3 /docker/clawsum/scripts/paperclip-pause-all-work.py
```

## Escalation

Enabling heartbeats = Tier 2 approval from Gerald.
