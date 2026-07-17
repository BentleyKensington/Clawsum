# OpenAI auth — API key vs ChatGPT/Codex subscription

## Locked policy (Clawsum)

| Priority | Method | Used for |
|----------|--------|----------|
| **1 — Primary** | **ChatGPT Plus via Codex OAuth** (`openai-codex`) | All 9 OpenClaw Telegram agents + Paperclip→gateway tasks |
| **2 — Backup only** | `OPENAI_API_KEY` (`openai:default`) | When Codex OAuth fails or expires |
| **Not used** | `ANTHROPIC_API_KEY` | Optional in `.env` for future Hermes; **OpenClaw agents do not use Anthropic today** |

Enforce on VPS after any auth change:

```bash
python3 /docker/clawsum/scripts/enforce-llm-codex-first.py
cd /docker/clawsum && docker compose restart openclaw-gateway
```

**Hermes exception:** tasks assigned to **Clawsum Hermes** use `openclaw_gateway` → session `paperclip:hermes` → **Codex** (same as Admin). Optional **Hermes dashboard** (`hermes dashboard`, :9119) is for exploration only — see [HERMES-OPENCLAW-ROUTING.md](./HERMES-OPENCLAW-ROUTING.md).

**OpenRouter escalation:** non-OpenAI models (Claude, Gemini, …) via `OPENROUTER_API_KEY` — see [OPENROUTER-AND-VOICE.md](./OPENROUTER-AND-VOICE.md).

---

## Why groups showed "missing API key"

Each specialist agent has its **own** auth store. Only `main` had a profile, and it was an empty **nexos** key — not OpenAI. The **Codex** plugin was also disabled.

**Fixed on server:**
- Codex plugin enabled
- `openai:default` API key profile written for all 9 agents (from `.env`)
- `auth.order.openai` prefers Codex OAuth, then API key

## ChatGPT subscription (recommended — no API billing)

Agent turns use the **Codex harness**, which needs **ChatGPT sign-in**, not just `OPENAI_API_KEY`.

**One-time setup** (interactive — run from your PC):

```bash
ssh -t clawsum "cd /docker/clawsum && docker compose run --rm openclaw-cli models auth login --provider openai-codex --device-code"
```

Follow the URL/code in the terminal (ChatGPT account). Then sync to all agents:

```bash
ssh clawsum "python3 /docker/clawsum/scripts/setup-openai-codex-auth.py"
```

Restart gateway:

```bash
ssh clawsum "cd /docker/clawsum && docker compose restart openclaw-gateway"
```

Verify in Telegram: `@YourTelegramBot /status` — should show Codex runtime.

## API key only (already configured as fallback)

`OPENAI_API_KEY` in `/docker/clawsum/.env` is registered as `openai:default` on every agent. If Codex OAuth is not set up, some builds may still error until you complete device-code login above.

## Import ChatGPT history

OpenClaw does **not** merge exports into live Telegram sessions automatically. Use the **chatgpt-import** skill:

1. **Export** from ChatGPT: Settings → Data controls → Export data (ZIP with `conversations.json`).
2. **Upload ZIP** to the server, e.g. `/docker/clawsum/imports/chatgpt-export.zip`.
3. **Install skill** (on server):

   ```bash
   docker exec clawsum-openclaw-gateway-1 node dist/index.js skills install clawhub:@openclaw/chatgpt-import
   ```

   Or search ClawHub: `openclaw skills search chatgpt`

4. Ask **admin** in DM: *"Import my ChatGPT export from /home/node/imports/chatgpt-export.zip into memory archive."*

Imports go to **memory archive / searchable memory**, not into per-group session threads. Specialist agents can search that memory if configured.

Alternative: **chat-history-import** skill for JSONL normalization across providers.
