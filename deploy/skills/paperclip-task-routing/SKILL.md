---
name: paperclip-task-routing
description: Creates and assigns Paperclip issues to the correct cell agent with acceptance criteria. Use when Hermes or Admin turns intent into governed work.
agents: [admin, paperclip, hermes, planning]
cells: ["*"]
tier_autonomous: 1
credentials: [PAPERCLIP_API, PAPERCLIP_COMPANY_ID]
approval_actions: []
---

# Paperclip task routing

## Instructions

1. Identify `ops.businesses.slug` (cell). If unknown → ask Boss.
2. Choose assignee from skill domain (GHL→ghl, deploy→coding, etc.).
3. Create issue with: title, cell slug in body, acceptance criteria, risk tier note.
4. If Tier 2 action implied → also create `ops.approvals` row.
5. Do not assign **Clawsum Hermes** unless issue says `Boss authorized Hermes: yes`.

## Scripts

```bash
python3 /docker/clawsum/scripts/paperclip-create-tasks.py
python3 /docker/clawsum/scripts/paperclip-analyze-assign-boss.py --gmail-pending
```
