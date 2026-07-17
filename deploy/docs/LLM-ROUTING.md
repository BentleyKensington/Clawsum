# LLM routing — how Clawsum picks a model

**Policy:** OpenAI/GPT → **Codex or direct API**. Everything else → **OpenRouter** (or optional **NVIDIA NIM** direct). No automatic spend escalation without a signal.

Related: [OPENAI-AUTH.md](./OPENAI-AUTH.md) · [OPENROUTER-AND-VOICE.md](./OPENROUTER-AND-VOICE.md)

---

## Decision layers (best order)

```text
1. Workload type     → default lane (interactive vs batch vs long-job)
2. Task metadata     → Paperclip label llm:* on the issue
3. Agent policy      → SOUL/ESCALATION (ask Boss before frontier)
4. Automatic fallback→ only when primary provider errors (OpenClaw)
5. Manual override   → Boss /model or script --escalate
```

The system should **not** silently jump to expensive frontier models on “hard” prompts. Use explicit **labels** or **flags**.

---

## Lanes

| Lane | When | Model | Billing |
|------|------|-------|---------|
| **interactive** | Telegram, OpenClaw turns, Paperclip→gateway agents | `openai/gpt-5.4` Codex | ChatGPT Plus |
| **interactive-fallback** | Codex missing / rate limit | `openai/gpt-5.4` API | OpenAI API |
| **batch-cheap** | Crons, triage, analyze-assign | `gpt-4o-mini` | OpenAI API |
| **batch-free** | High volume, low stakes, Boss label `llm:cheap` | OpenRouter `:free` models | OpenRouter free tier |
| **escalation** | Label `llm:frontier`, `--escalate`, or OpenClaw fallback | Claude / Gemini / etc. via OR | OpenRouter credits |
| **coding** | Label `llm:coding`, Coding agent long jobs | Qwen3 Coder, Devstral via OR | OpenRouter |
| **multilingual** | Label `llm:glm`, Chinese/EN heavy | `z-ai/glm-*` via OR or NIM direct | OR / NVIDIA |

---

## OpenRouter model examples (env slugs, no `openrouter/` prefix)

```env
# Escalation / frontier (paid, high quality)
OPENROUTER_ESCALATION_MODEL=anthropic/claude-sonnet-4-6
OPENROUTER_CODING_MODEL=qwen/qwen3-coder
OPENROUTER_RESEARCH_MODEL=google/gemini-2.5-pro

# Free / cheap (OpenRouter :free suffix — roster rotates)
OPENROUTER_FREE_MODEL=openrouter/free
OPENROUTER_CHEAP_MODEL=z-ai/glm-4.5-air:free
OPENROUTER_CHEAP_CODING_MODEL=qwen/qwen3-coder:free
```

Browse current free list: [openrouter.ai/models](https://openrouter.ai/models?max_price=0)

**NVIDIA Nemotron / GLM on OpenRouter:** often appear as `nvidia/*:free` or partner slugs — add to `.env` when you pick favorites.

---

## NVIDIA NIM (optional second path)

NVIDIA offers free-tier models at [build.nvidia.com](https://build.nvidia.com) with an **OpenAI-compatible** API.

| Approach | Pros | Cons |
|----------|------|------|
| **OpenRouter only** | One key, one client, free `:free` models include Nemotron | Rate limits; roster changes |
| **NIM direct** | Direct access to GLM-5, Kimi, etc. on NIM catalog | Second key + base URL; not wired in OpenClaw yet |

Optional `.env`:

```env
NVIDIA_NIM_API_KEY=
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_DEFAULT_MODEL=zhipuai/glm-4.7
```

Use in batch scripts only initially (same pattern as `openrouter_client.py`). OpenClaw agents stay on Codex unless Boss switches `/model`.

---

## Why crons don't use GPT/Codex

| Reason | Detail |
|--------|--------|
| **Codex = interactive OAuth** | Tied to ChatGPT device login in OpenClaw gateway — not a headless API for `cron` |
| **Crons run on VPS host** | `gmail-triage.py`, `daily-global-report.py` — no gateway WebSocket session |
| **Cost control** | Batch jobs use `gpt-4o-mini` API or OpenRouter `:free` — predictable per-token |
| **Could route via gateway?** | Possible but heavy: HTTP to OpenClaw, session limits, still may not bill as Plus |

**Exception:** If Boss assigns a **Paperclip task** to an OpenClaw agent, that run uses Codex when the heartbeat fires — that's task execution, not cron.

---

## Who sets `llm:*` labels?

| Stage | Who | How |
|-------|-----|-----|
| **Auto-triage** | `paperclip-analyze-assign-boss.py` | LLM suggests `llm_tier` → writes `llm:cheap` etc. in task description |
| **Boss override** | You | Edit task description: `llm:frontier` for one hard job |
| **Agent read** | OpenClaw agents (future) | Parse task text before `/model` switch |
| **Cron scripts** | `llm_policy.resolve_batch_model()` | Reads `llm:*` from env or task export |

Paperclip does **not** have native label types yet — we embed `llm:tier` in the **issue description** (machine-readable line).

---

## How actual model is chosen

```text
llm:cheap in task text
    → llm_policy.parse_llm_lane()
    → lane "cheap"
    → env OPENROUTER_CHEAP_MODEL or default z-ai/glm-4.5-air:free
    → openrouter_client.chat(..., model=slug)
```

| `llm:*` | Provider | Env key | Default slug |
|---------|----------|---------|--------------|
| `default` | OpenAI API | `GMAIL_TRIAGE_MODEL` | `gpt-4o-mini` |
| `cheap` / `free` | OpenRouter | `OPENROUTER_CHEAP_MODEL` / `OPENROUTER_FREE_MODEL` | `z-ai/glm-4.5-air:free` |
| `frontier` | OpenRouter | `OPENROUTER_ESCALATION_MODEL` | `anthropic/claude-sonnet-4-6` |
| `coding` | OpenRouter | `OPENROUTER_CODING_MODEL` | `qwen/qwen3-coder` |
| `research` | OpenRouter | `OPENROUTER_RESEARCH_MODEL` | `google/gemini-2.5-pro` |
| `glm` | OpenRouter | `OPENROUTER_CHEAP_MODEL` | GLM free tier |

Interactive OpenClaw chat **ignores** task labels unless agent is told to read them — labels primarily drive **batch/cron** and future agent policy.

---

## NVIDIA / GLM / rising stars

All non-GPT paths go through **OpenRouter** (one key) or optional **NVIDIA NIM** direct for batch only. See env `OPENROUTER_FREE_MODEL`, `OPENROUTER_CHEAP_MODEL`, `NVIDIA_NIM_*`.

---

Add to issue description or Paperclip labels:

| Label | Meaning |
|-------|---------|
| `llm:default` | Codex / gpt-5.4 path (no extra cost) |
| `llm:cheap` | OpenRouter free or `:floor` for this task |
| `llm:frontier` | OpenRouter escalation model — Boss pre-approved |
| `llm:coding` | OpenRouter coding model |
| `llm:glm` | GLM / multilingual via OR or NIM |

`paperclip-analyze-assign-boss.py` can suggest these when classifying Boss backlog (future wiring).

---

## What is implemented vs planned

| Piece | Status |
|-------|--------|
| Codex first + API fallback | ✅ `enforce-llm-codex-first.py` |
| OpenRouter escalation fallbacks in OpenClaw | ✅ scaffold; needs `OPENROUTER_API_KEY` on VPS |
| `openrouter_client.py` for batch scripts | ✅ |
| Batch default `gpt-4o-mini` | ✅ gmail-triage, ghl-audit, analyze-assign |
| Task label → model router | ⬜ convention documented; agent read not wired |
| NIM direct client | ⬜ env only; add `nim_client.py` when key exists |
| Auto frontier on difficulty | ❌ intentionally not built (cost) |

---

## Apply on VPS

```bash
# 1. Add keys to .env (see env.openrouter-voice.example)
# 2. Apply OpenClaw + OpenRouter config
python3 /docker/clawsum/scripts/enforce-llm-codex-first.py
cd /docker/clawsum && docker compose restart openclaw-gateway
```
