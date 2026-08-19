---
name: llm-free-vs-paid
description: Choose free/cheap vs paid frontier for a task. Default cheap; paid only on escalate, llm:frontier, or provider failure.
agents: [llm-lab, hermes, coding, research]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [OPENROUTER_*, OPENAI_*]
approval_actions: []
---

# LLM free vs paid

See [LLM-LAB.md](../../docs/LLM-LAB.md) · [LLM-ROUTING.md](../../docs/LLM-ROUTING.md).

## When to use

Routing a job, writing `llm:*` on a Paperclip issue, or Boss asks “can we do this for free?”

## Instructions

1. Classify: interactive vs batch vs voice vs coding vs research vs “must be brilliant.”
2. Default:
   - Interactive → Codex
   - Batch → mini or OpenRouter `:free`
   - Coding → `llm:coding` (OR coder models)
   - Deep research with repos/compare → `llm:research` (Gemini Pro) — **tell Boss it costs**
3. Paid frontier only if: standalone word `escalate`, label `llm:frontier`, or primary provider error.
4. Write the recommendation as a one-liner on the issue: `llm:cheap` | `llm:coding` | `llm:research` | `llm:frontier`.
5. Never switch gateway default model yourself.

## Escalation

Estimated paid eval > ~$5 → notify Boss first.
