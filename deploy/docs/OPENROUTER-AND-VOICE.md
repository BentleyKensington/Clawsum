# OpenRouter escalation and on-demand speech

Clawsum routes **OpenAI/GPT through Codex or direct OpenAI API** — never through OpenRouter.  
**OpenRouter** is the escalation path for **non-OpenAI models** (Claude, Gemini, GLM, Nemotron free tier, etc.).

**Model selection policy:** [LLM-ROUTING.md](./LLM-ROUTING.md)

---

## LLM routing matrix

| Need | Path | Billing |
|------|------|---------|
| Default agent chat | `openai/gpt-5.4` via **Codex OAuth** | ChatGPT Plus subscription |
| GPT fallback | `openai:default` (`OPENAI_API_KEY`) | OpenAI API |
| Escalation / non-GPT | `openrouter/<author>/<model>` fallbacks | OpenRouter credits |
| Batch crons (cheap) | `OPENAI_API_KEY` + `gpt-4o-mini` | OpenAI API |
| Batch escalation | `openrouter_client.py` | OpenRouter credits |

**Do not** set `openrouter/openai/*` as escalation models — that defeats the policy.

---

## Setup (VPS)

1. Add keys to `.env` (see `deploy/env.openrouter-voice.example`):

   ```bash
   OPENROUTER_API_KEY=sk-or-...
   OPENROUTER_ESCALATION_MODEL=anthropic/claude-sonnet-4-6
   ```

2. Apply policy:

   ```bash
   python3 /docker/clawsum/scripts/enforce-llm-codex-first.py
   cd /docker/clawsum && docker compose restart openclaw-gateway
   ```

   `enforce-llm-codex-first.py` calls `configure-openrouter-escalation.py` when `OPENROUTER_API_KEY` is set.

3. Verify in Telegram admin DM: `/status` and `/model` — escalation models should appear in the catalog.

---

## How escalation works (OpenClaw)

`configure-openrouter-escalation.py` sets:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "openai/gpt-5.4",
        "fallbacks": [
          "openrouter/anthropic/claude-sonnet-4-6",
          "openrouter/google/gemini-2.5-pro"
        ]
      }
    }
  }
}
```

- **Primary** always uses OpenAI auth order: Codex → API key.
- **Fallbacks** run only when the primary model path fails (provider error, rate limit, etc.).
- Boss can also switch model per session: `/model openrouter/anthropic/claude-sonnet-4-6`.

Per-agent overrides: set `agents.list[].model` in `openclaw.json` (e.g. Coding → `OPENROUTER_CODING_MODEL`).

---

## Batch scripts (Python)

Use `openrouter_client.py` for non-GPT work in crons:

```python
from openrouter_client import chat_text

summary = chat_text(
    [{"role": "user", "content": prompt}],
    model="anthropic/claude-sonnet-4-6",
)
```

Raises if you pass an `openai/*` slug — use `OPENAI_API_KEY` for GPT in scripts.

---

## Speech on demand

OpenClaw gateway reads `.env` via `env_file`. TTS auto-reply is **off** by default (`messages.tts.auto: off`).

### CLI (VPS)

```bash
# STT — OpenAI Whisper (default)
python3 scripts/speech_api.py stt --input recording.wav

# STT — multimodal via OpenRouter
SPEECH_STT_PROVIDER=openrouter python3 scripts/speech_api.py stt --input recording.wav

# TTS — OpenAI
python3 scripts/speech_api.py tts --text "Daily report ready" --output report.mp3

# TTS — ElevenLabs
python3 scripts/speech_api.py tts --text "Hello" --provider elevenlabs --output hi.mp3
```

### OpenClaw Telegram

- `/tts on` / `/tts off` — per-chat auto speech
- `/tts audio <text>` — one-shot TTS reply
- Provider from `SPEECH_TTS_PROVIDER` (`openai` or `elevenlabs`)

Requires `OPENAI_API_KEY` and/or `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` in `.env`.

---

## Env reference

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Required for escalation |
| `OPENROUTER_ESCALATION_MODEL` | Default non-GPT fallback |
| `OPENROUTER_CODING_MODEL` | Optional specialist fallback |
| `OPENROUTER_RESEARCH_MODEL` | Optional specialist fallback |
| `SPEECH_STT_PROVIDER` | `openai` or `openrouter` |
| `SPEECH_TTS_PROVIDER` | `openai` or `elevenlabs` |
| `OPENAI_STT_MODEL` | Default `whisper-1` |
| `OPENAI_TTS_MODEL` | Default `gpt-4o-mini-tts` |
| `ELEVENLABS_*` | ElevenLabs TTS |

---

## Related

- [OPENAI-AUTH.md](./OPENAI-AUTH.md) — Codex first policy
- [PLATFORM-DEPLOY-TEMPLATE.md](./PLATFORM-DEPLOY-TEMPLATE.md) — LLM table
- [HERMES-POLICY.md](./HERMES-POLICY.md) — long-job assignee
