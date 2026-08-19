---
name: deepgram-voice-eval
description: Compare Deepgram Flux STT/TTS vs Nova, Aura, ElevenLabs, OpenAI TTS for Vocalitic/VAPI. Hosted API first; no unofficial RE.
agents: [llm-lab, vocalitic, vapi, coding]
cells: [clawsum-platform, vocalitic]
tier_autonomous: 1
credentials: [DEEPGRAM_*, ELEVENLABS_*, OPENAI_*, VAPI_*]
approval_actions: [paid_eval]
---

# Deepgram voice eval

See [DEEPGRAM-AND-VOICE-STACK.md](../../docs/DEEPGRAM-AND-VOICE-STACK.md).

## When to use

New Deepgram release, Vocalitic quality complaint, or VAPI transcriber/voice swap.

## Instructions

1. Confirm `DEEPGRAM_API_KEY` present (do not print it).
2. Use Flux (`/v2/listen`, `/v2/speak`) for **agent** loops; Nova-3 for **meetings/archive**.
3. Score on a frozen clip set under `data/llm-lab/voice-clips/` (create if missing): latency, barge-in, WER, $/min, voice match to Jarvis.
4. Write scorecard to Obsidian `LLM-Lab/voice-eval-YYYY-MM-DD.md`.
5. Recommend Vocalitic default path; apply = Tier 2.

Self-host Flux needs dedicated Ampere+ GPU — not the current VPS job.

## Escalation

Paid minutes → tell Boss. Missing key → stop.
