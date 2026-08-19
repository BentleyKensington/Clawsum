---
name: agent-daily-review
description: Each agent reviews memory, tasks, research; suggests skills; feeds morning brief.
agents: [hermes, admin, planning]
cells: [*]
tier_autonomous: 1
credentials: [PAPERCLIP_*, POSTGRES_*]
approval_actions: []
status: shell
---

# agent-daily-review

**Status:** shell — populate runbooks as the agent learns.

## When to use

Each agent reviews memory, tasks, research; suggests skills; feeds morning brief.

## Instructions

1. Read related memory + open Paperclip issues for this domain.
2. Draft the next move; do not take Tier 2+ actions.
3. Suggest skill improvements on the daily review.

## Escalation

Tier 2+ (send, spend, legal file, pay) → Boss Approve All.
