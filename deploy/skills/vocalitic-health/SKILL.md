---
name: vocalitic-health
description: Diagnoses Vocalitic voice AI health — latency, SignalWire, STT/TTS/LLM errors. Use for uptime, call quality, or infra incidents on the vocalitic cell.
agents: [coding, admin]
cells: [vocalitic, hardware-local-ai]
tier_autonomous: 0
credentials: [POSTGRES_*, OPENCLAW_*]
approval_actions: [restart_noncritical, production_deploy, model_change]
---

# Vocalitic health

## Tier 0

- Read health endpoints / logs / Grafana.
- Draft diagnosis + recommended action.

## Tier 2+

- Restart, model swap, prod deploy → approval required.
- Never delete call data or wipe logs autonomously.
