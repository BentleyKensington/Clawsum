---
name: research-brief
description: Produces competitive or market research briefs without writing to production systems. Use when Boss or Planning asks for research, competitor scans, or decision memos.
agents: [research, planning, admin, hermes]
cells: ["*"]
tier_autonomous: 0
credentials: [OPENAI_*/OPENROUTER_* optional]
approval_actions: []
---

# Research brief

1. Clarify question + cell context.
2. Gather only public / allowed sources.
3. Output: summary, findings, risks, recommended next Paperclip tasks.
4. No outbound client mail from this skill.
