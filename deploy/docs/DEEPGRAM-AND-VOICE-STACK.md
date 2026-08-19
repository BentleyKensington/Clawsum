# Deepgram Flux / TTS and Clawsum voice stack

**As of:** 2026-08-19  
**Owner:** OpenClaw `llm-lab` (+ Vocalitic for product apply)  
**Email attachments:** not in this workspace. Re-run `python3 scripts/gmail-topic-scan.py --query deepgram --since today` on the VPS after Gmail sync. Findings below are from Deepgram public docs.

Related: [LLM-LAB.md](./LLM-LAB.md) · [OPENROUTER-AND-VOICE.md](./OPENROUTER-AND-VOICE.md) · Vocalitic `vocalitic-product-ops`

---

## What changed (why Flux matters)

Deepgram split **conversation agents** from **transcription products**.

| Product | Endpoint | Job |
|---------|----------|-----|
| **Flux STT** | `/v2/listen` | Voice agents. Built-in turn events: StartOfTurn, EagerEndOfTurn, EndOfTurn, SpeechResumed. No external VAD. |
| **Nova-3 STT** | `/v1/listen` | Meetings, captions, pre-recorded, diarization, 54 languages, analytics |
| **Flux TTS** | `/v2/speak` (WS + REST) | Agent TTS: stream LLM tokens in, barge-in `Interrupt` reports `text_spoken` |
| **Aura-1 / Aura-2 TTS** | prior `/v1/speak` | General TTS; migrate agents to Flux TTS when ready |

Flux STT is **not** a drop-in Nova. No meeting mode, no diarization, no smart formatting. It is the right default **inside Vocalitic / VAPI-style loops**.

Self-host constraints:

- Flux **cannot share a GPU node** with Nova/Aura.
- Flux STT: Ampere+ (A10, L4, L40S, A100, H100). **T4 = no**.
- Flux TTS: L4 / L40S / A100 / H100 (not T4, not A10). Early Access self-host.

NVIDIA shows up two ways: (1) Deepgram Engine on NVIDIA GPUs, (2) Nemotron LLMs behind a Deepgram Voice Agent (AWS Bedrock demo). Clawsum already routes non-GPT LLMs through OpenRouter / optional NIM.

---

## Clawsum recommendation

| Workload | Default (cheap) | Paid / exception |
|----------|-----------------|------------------|
| Interactive chat | Codex GPT | `escalate` → Claude/Gemini Pro |
| Batch / cron | `gpt-4o-mini` or OpenRouter `:free` | `llm:frontier` |
| Voice agent STT | **Flux** (hosted API) until self-host GPU exists | Nova-3 only for meetings/archive |
| Voice agent TTS | Flux TTS **or** keep ElevenLabs until bake-off | ElevenLabs custom voice if Boss prefers current Jarvis timbre |
| Jarvis cockpit TTS | ElevenLabs (already wired) | Don’t swap without A/B |
| Local/dev STT | Faster Whisper (media already) | Not for sub-300ms calls |

**Rule:** Vocalitic production voice path should be evaluated as Flux STT + (Flux TTS **or** ElevenLabs) + cheap LLM, with frontier LLM only on hard turns.

Weekly `llm-research-watch.py` re-checks Deepgram, NVIDIA NIM, OpenRouter `:free`, and Whisper/Parakeet releases.

---

## Bake-off (when keys exist)

Use skill `deepgram-voice-eval`. Score: time-to-first-audio, barge-in correctness, WER on a 10-clip Vocalitic set, $ / minute, English + any second language Boss cares about.

Do **not** burn Flux self-host GPUs on the VPS. Hosted API first.

---

## Env (placeholders only)

```env
DEEPGRAM_API_KEY=
DEEPGRAM_STT_MODEL=flux-general-en
DEEPGRAM_TTS_MODEL=flux
# Optional NIM for LLM slot in voice agents
NVIDIA_NIM_API_KEY=
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
```

Never commit values. Restart `openclaw-gateway` after editing VPS `.env`.
