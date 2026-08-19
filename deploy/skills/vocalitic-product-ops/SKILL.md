---
name: vocalitic-product-ops
description: Operate Vocalitic as a product — read v1m12 codebase, dashboard, logs via SSH; recommend changes for Boss approval.
agents: [vocalitic, coding, admin]
cells: [vocalitic, hardware-local-ai]
tier_autonomous: 1
credentials: [VOCALITIC_SSH_*, VOCALITIC_CODEBASE_PATH, POSTGRES_*]
approval_actions: [production_deploy, restart_noncritical, model_change]
---

# Vocalitic product ops

See [PRODUCT-AGENTS.md](../../docs/PRODUCT-AGENTS.md).

## When to use

Health, feature requests, dashboard oddities, STT/TTS/LLM routing inside Vocalitic.

## Instructions

1. Read local/VPS codebase at `$VOCALITIC_CODEBASE_PATH` (default **`C:\APPS\V1m12`**, app source `v1m12/`, deploy `DEPLOY.md`, dashboard `v1m12/dashboard/dashboard_server.py` port 9080, live host `app1.vocalitic.com` on `69.62.64.214`). If unset, ask for the path — do not guess other repos.
2. Required reading: `DEPLOY.md`, `v1m12/src/bot.py`, dashboard, STT/TTS/LLM path (`remote_tts.py`, prompt manager).
3. SSH via `product-ssh-ops` to `69.62.64.214` (read-only): `/opt/apps/app1`, `/opt/traefik`. Collect process list, recent logs (redact secrets), health URL.
4. Compare dashboard vs code. File **observations** in Obsidian `Vocalitic/` and a Paperclip issue with recommended diffs.
5. Do not deploy, restart prod, or change models without Tier 2.

## Training corpus

- This skill + `vocalitic-health`
- Repo tree under v1m12 (when path exists)
- [DEEPGRAM-AND-VOICE-STACK.md](../../docs/DEEPGRAM-AND-VOICE-STACK.md) for voice vendor choice

## Escalation

Missing SSH key/path → one question. Outage → notify Admin/Rocco; still no silent restart.
