---
name: hardware-local-ai
description: Diagnostics for local GPU / model servers supporting Vocalitic and local inference. Use for VRAM, uptime, Ollama/vLLM issues.
agents: [coding, admin]
cells: [hardware-local-ai, vocalitic]
tier_autonomous: 0
credentials: [host/docker access]
approval_actions: [restart_container, model_change, production_deploy]
---

# Hardware / local AI

- Tier 0: report VRAM, container health, error tails.
- Restarts / model changes → approval.
- Never wipe model caches or call data autonomously.
