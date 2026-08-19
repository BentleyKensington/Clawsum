---
name: llm-compare
description: Bake-off models on a frozen prompt set; write scorecard. Paid eval = notify Boss.
agents: [llm-lab, coding, research]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [OPENAI_*, OPENROUTER_*]
approval_actions: [paid_eval]
---

# llm-compare

See [LLM-LAB.md](../../docs/LLM-LAB.md).

## When to use

Weekly watch found a new free/mid model, or Boss wants a bake-off.

## Instructions

1. Use frozen prompts in `data/llm-lab/prompts/` (create 5 if missing: ops brief, code fix, research synthesis, refusal/safety, tool-planning).
2. Run cheap/free first; frontier only if Boss approved spend.
3. Score: correctness, citations, latency, $ estimate. Winner per lane (chat/coding/research).
4. Write `obsidian/LLM-Lab/scorecard-YYYY-MM-DD.md`. Propose env slug changes; do not apply.

## Escalation

Paid eval > ~$5 → notify first. Never change gateway default model.
