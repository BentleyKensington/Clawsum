---
name: llm-research-watch
description: Weekly or on-demand scan of OpenRouter free models, NVIDIA NIM, Deepgram Flux/TTS, and other releases that change Clawsum routing.
agents: [llm-lab, research, coding]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [OPENROUTER_*, NVIDIA_NIM_*, DEEPGRAM_*]
approval_actions: []
---

# LLM / voice research watch

## When to use

Sunday cron, Boss “what changed in models?”, Vocalitic latency incident, or Deepgram/NVIDIA email.

## Instructions

```bash
python3 /docker/clawsum/scripts/llm-research-watch.py --now
```

1. OpenRouter models with `max_price=0` — note adds/drops vs last run (`data/llm-lab/last-watch.json`).
2. NVIDIA NIM / Nemotron catalog highlights (build.nvidia.com).
3. Deepgram Flux STT/TTS vs Nova/Aura (see [DEEPGRAM-AND-VOICE-STACK.md](../../docs/DEEPGRAM-AND-VOICE-STACK.md)).
4. Whisper / Parakeet / other local STT only as a footnote unless Boss un-defers local GPU.
5. Write Obsidian `LLM-Lab/YYYY-MM-DD-watch.md` and a Paperclip comment on the standing LLM Lab issue (create if missing).
6. Propose `.env` slug changes; do not apply.

If Gmail has Deepgram images today:

```bash
python3 /docker/clawsum/scripts/gmail-topic-scan.py --query deepgram --since today --markdown
```

Analyze attachments if MinIO/Postgres stored them. Do not invent what the email showed.

## Escalation

Paid API probes = notify. No silent spend.
