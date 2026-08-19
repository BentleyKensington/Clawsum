---
name: inbound-adopt-evaluate
description: Evaluate inbound email, repos, mockups, and tools for Clawsum adoption. Compare layer-by-layer (UI vs board vs runtime vs skill factory). Never dismiss useful overlap.
agents: [research, planning, hermes, admin, coding]
cells: [clawsum-platform, techtasia]
tier_autonomous: 1
credentials: [OPENAI_*, POSTGRES_*, PAPERCLIP_API]
approval_actions: [production_deploy]
---

# Inbound adopt / evaluate

Clawsum improves by stealing what is better. Overlap is a comparison, not a veto.

## Layers (always name them)

| Layer | Clawsum today | Typical inbound |
|-------|---------------|-----------------|
| CEO chat / cockpit UI | Hermes | dashboards, mockups, control apps |
| Task board / approvals | Paperclip | Linear/Jira clones |
| Agent runtime | OpenClaw | other gateways |
| Skill / team factory | mostly manual scripts | RevFactory Harness, Archon |
| Memory / archive | Postgres + Arcade + dream | other RAG |

## Verdicts

- **adopt** — stand it up or port it in
- **side_by_side** — test beside the current layer
- **steal_ideas** — copy the pattern into a Clawsum skill/agent
- **skip_noise** — marketing / noreply only

## Instructions

1. Read the material (email body, README, image analysis).
2. Write HOW it overlaps each layer — not “we already have agents.”
3. Assign `project_slug` + owner agent.
4. If mockup: say what cockpit screen should change.
5. Name skills to grow (`skill-forge` if a new skill is needed).
6. Open or update a Paperclip issue; do not silently ignore.

```bash
python3 /docker/clawsum/scripts/gmail-inbox-review.py --inbox-only --limit 12
python3 /docker/clawsum/scripts/paperclip-analyze-assign-boss.py --force --limit 20
```

## Escalation

Prod install / replacing Hermes or OpenClaw = Tier 2 (Boss Approve All).
