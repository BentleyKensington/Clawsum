---
name: spec-interview
description: Interview Boss until a spec card is complete, then open or update a Paperclip issue. Use when the ask is fuzzy, multi-agent, or missing success/owner/tier.
agents: [hermes, admin, planning]
cells: [clawsum-platform, personal-admin, vocalitic, acceptai-fastbuy, sellthebizfast]
tier_autonomous: 1
credentials: [PAPERCLIP_*, POSTGRES_*]
approval_actions: [create_issue_bulk]
---

# Spec interview

See [INTERVIEW-UNTIL-CRISP.md](../../docs/INTERVIEW-UNTIL-CRISP.md).

## When to use

Gerald asked for a build, agent, integration, or “make it so” without Goal / Success / Out of scope / Owner.

## Instructions

1. Restate the ask in one sentence.
2. Pull existing truth (do not re-ask):

```bash
python3 /docker/clawsum/scripts/gmail-inbox-review.py --inbox-only --markdown --no-per-email-report
python3 /docker/clawsum/scripts/archive-proactive-brief.py --markdown
python3 /docker/clawsum/scripts/gmail-task-link.py --markdown
```

3. Fill the spec card. Ask **one** missing field per turn.
4. Create/update Paperclip; paste the card in the description. Link CLA ids and email subjects (no raw bodies in Discord).
5. Do not start Tier 2+ work.

## Escalation

Unclear cell → ask Boss. Personal archive → Admin/Hermes only.
