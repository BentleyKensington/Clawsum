# Deepgram Flux / TTS and Clawsum voice stack

**As of:** 2026-08-19  
**Owner:** OpenClaw `llm-lab` (+ Vocalitic for product apply)  
**Today’s mail (ops.emails id 64903, 2026-08-19 21:01 UTC):** Gerald (Red Rover) forwarded Deepgram+Twilio webinar photos. Gmail stored **Google Drive links**, not MIME attachments (`attachments=[]`). Caption: “Deepgram flux stt with Deepgram tts and more.” Screenshots reviewed below.

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

## Webinar 2026-08-19 (Deepgram + Twilio) — what the photos actually say

Presenters: **Theresa Foy** (Deepgram) and **Michael Carpenter**. Thesis: **Twilio carries the call; Deepgram makes the conversation.** Operating phone calls is the hard part — web demos never pay the PSTN tax.

### Six problems (their frame)

1. Audio path tax: hops, codecs, jitter.
2. Real callers break turn-taking (interrupt, trail-off, noise, speakerphone).
3. Machines answer (AMD / voicemail) — most agents have no plan.
4. Answered + compliant: spam flags, STIR/SHAKEN, consent, calling windows.
5. Plumbing eats the roadmap (streaming, barge-in, conversational state).
6. Flying blind after launch without call-level insight.

### Their stack (maps to Vocalitic / VAPI)

Audio in (PSTN/SIP) → **Flux STT** (transcripts **+ turn events**) → **LLM of your choice with function calling** → **Deepgram TTS** (or BYO TTS) → audio out.

**Voice Agent API** (`wss://agent.deepgram.com/v1/agent/converse`): one connection that orchestrates STT + LLM + TTS + barge-in. Slides say **bring your own LLM or TTS and swap mid-call**. Function calling mid-call (CRM, slots, book/confirm). After-call: Twilio Conversational Intelligence for summaries/webhooks.

**Flux differentiator they sold:** turn events not just transcripts; native barge-in; trail-off; thresholds tunable mid-stream. Collocate STT/LLM/TTS/turn detection so there are **no extra hops between services**.

Demo they showed: dental scheduling dashboard, inbound/outbound, function `Check Available Slots`, live transcript. Playground: [playground.deepgram.com](https://playground.deepgram.com). Console: [console.deepgram.com](https://console.deepgram.com). Docs: [developers.deepgram.com/docs](https://developers.deepgram.com/docs). Reference: [inbound telephony agent](https://developers.deepgram.com/docs/inbound-telephony-agent.md) (Flux `flux-general-en`, Twilio Media Streams, MIT).

### Clawsum takeaway vs VAPI

| Path | Use when |
|------|----------|
| **Vocalitic today** | Keep current SignalWire/Twilio-style media path; evaluate **Flux STT** in the listen slot before ripping TTS. |
| **Deepgram Voice Agent API** | Fastest “one socket” phone agent if we want Deepgram to own barge-in. Still BYO LLM (cheap default). |
| **VAPI** | Separate company/agent for the VAPI **account**. Do not duplicate Deepgram Voice Agent and VAPI as two production runtimes for the same number without a spec-interview. |

AMD, branded calling, and STIR/SHAKEN are **Twilio Trust Hub** problems, not LLM problems. Put those on Vocalitic/VAPI runbooks, not LLM Lab.

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
