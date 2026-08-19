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

1. Clarify question + cell context. Consult ChatGPT archive (`consult_archive` / Inbox analyst hits) so we do not re-litigate decided work.
2. Gather only public / allowed sources.
3. If the topic is deep (repos, adopt/compare, architecture) or GPT looks thin, escalate to `OPENROUTER_RESEARCH_MODEL` (Gemini 2.5 Pro) then `OPENROUTER_ESCALATION_MODEL`.
4. Output: summary, findings, how it compares to Clawsum layers, adopt/side-by-side/steal, recommended next Paperclip tasks.
5. If anything is unclear, ask leading improvement questions — not a blank interrogation.
6. No outbound client mail from this skill.
