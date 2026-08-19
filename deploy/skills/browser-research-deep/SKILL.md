---
name: browser-research-deep
description: Deep research with OpenClaw browser + cheap LLM first; escalate to research/frontier models only when the cheap pass is thin or Boss says escalate.
agents: [research, llm-lab, sellthebizfast, hermes]
cells: ["*"]
tier_autonomous: 0
credentials: [OPENROUTER_*, OPENAI_*]
approval_actions: []
---

# Browser + deep research

## When to use

Vendor docs, competitive briefs, acquisition public info, model cards, API changelogs.

## Instructions

1. Use OpenClaw **browser** on official docs first (Deepgram, VAPI, CloseBot, Ring developer, OpenRouter models).
2. Draft a brief with sources. Lane: `llm:cheap` or Codex.
3. If the answer is thin, contradictory, or legal/numeric-critical: label `llm:research` or wait for Boss `escalate`.
4. Do not scrape behind logins Gerald did not authorize. Do not pull private CIMs from random file hosts.
5. File Obsidian under the owning agent folder.

Bright Data / heavy scrape = Data `data-scraper` (spend aware), not this skill.
