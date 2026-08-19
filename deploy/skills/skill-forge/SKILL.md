---
name: skill-forge
description: Turn a decided idea, repo, mockup, or workflow into a Clawsum skill + agent training so someone can actually execute it. Use after inbound-adopt-evaluate says adopt or steal_ideas.
agents: [coding, planning, admin, hermes]
cells: [clawsum-platform, techtasia]
tier_autonomous: 1
credentials: [PAPERCLIP_API]
approval_actions: [production_deploy]
---

# Skill forge (train the platform)

Gerald wants agents that can **develop and execute** the work, not just describe it.

## When to use

- Inbox/research said adopt / side_by_side / steal_ideas
- A new cell, workflow, or UI mockup needs a repeatable playbook
- An agent keeps failing because it has no skill

## What to produce

1. `deploy/skills/<id>/SKILL.md` from `_template` (frontmatter + steps + scripts + tier).
2. One row in `deploy/skills/CATALOG.md` and the agent→skills table.
3. Paperclip issue assigned to the executing agent with definition of done.
4. If it is a new OpenClaw agent: follow `openclaw-agent-config` (Tier 2 to ship live).
5. Short training note in the agent workspace (`WORKFLOWS.md` or cell overlay) — when to load the skill.

## Pattern to steal (RevFactory Harness)

Harness (Claude Code plugin) turns one sentence into `.claude/agents/` + `.claude/skills/` using six team patterns (pipeline, fan-out, expert pool, producer-reviewer, supervisor, hierarchy). Clawsum equivalent:

- Agents → OpenClaw ids + Paperclip assignees (not `.claude/agents/`)
- Skills → `deploy/skills/*/SKILL.md`
- Orchestration → Hermes W2 batch gate + Paperclip
- Validation → dry-run script + Boss Approve All

Do **not** replace Hermes/OpenClaw. Forge the factory **on top** of them.

## Escalation

Live gateway/agent create = Tier 2. Skill markdown only = Tier 1.
