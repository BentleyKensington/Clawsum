# Credentials & secrets exclusion policy

**Rule:** The Clawsum **template repo** must never contain live credentials, OAuth tokens, or instance `.env` files. All secrets live on the VPS in `.env` and runtime data directories only.

---

## Confirmed excluded from git (`.gitignore`)

| Pattern | What it protects |
|---------|------------------|
| `.env`, `.env.*` | All instance secrets (DB, API keys, PIT, JWT) |
| `data/` | Postgres data, OpenClaw workspaces, OAuth stores |
| `paperclip-data/` | Paperclip instance state |
| `**/.openclaw/`, `**/.openclaw-auth-secrets/` | OpenClaw config + auth on disk |
| `**/auth-profiles.json`, `**/codex-home/` | Codex OAuth profiles |
| `*.pem`, `*.key`, `credentials.json`, `secrets.json` | Key material |
| `obsidian/GHL/*-REI/`, `REI-GHL-AGENT-PLAYBOOK.md` | Instance vault content (overlay) |

**Allowed in git (placeholders only):**

- `deploy/env.example` — variable names, `change_me` placeholders  
- `deploy/env.ghl.example`, `deploy/env.gmail.example` — same  
- `deploy/config/ghl-accounts.json` — **no** PIT values, only `env_pit` key names  
- `deploy/config/ghl-accounts.instance.rei.example.json` — structure only  
- Postgres init SQL — `*_change_me` bootstrap passwords (rotated via `.env` on VPS)

---

## OAuth

| System | Where credentials live | In repo? |
|--------|------------------------|----------|
| **Codex / ChatGPT Plus** (OpenClaw agents) | Control UI sign-in → `data/.openclaw-auth-secrets/` | **No** |
| **Gmail (gog)** | Boss OAuth flow → instance paths in `.env` | **No** |
| **GHL PIT** | `.env` (`GHL_PIT`, `GHL_*_PIT`) | **No** |
| **Telegram bot** | `.env` (`TELEGRAM_BOT_TOKEN`) | **No** |
| **Paperclip JWT** | `.env` (`PAPERCLIP_AGENT_JWT_SECRET`, `BETTER_AUTH_SECRET`) | **No** |
| **OpenAI / Anthropic API** (crons, Hermes fallback) | `.env` optional keys | **No** |

OpenClaw agents use **Codex OAuth first**; `OPENAI_API_KEY` in `.env` is fallback only.  
**OpenRouter** (`OPENROUTER_API_KEY`) is for **non-OpenAI escalation** only — see [OPENROUTER-AND-VOICE.md](./OPENROUTER-AND-VOICE.md).

---

## Verification checklist

Before pushing or cloning to a new VPS:

- [ ] No `.env` file in working tree  
- [ ] `git status` does not show `data/`, `paperclip-data/`, or auth profiles  
- [ ] `deploy/config/ghl-accounts.json` has empty `telegram_group_id` and env **names** only  
- [ ] Example files use `pit-...`, `change_me`, or commented placeholders  
- [ ] Instance playbooks live under `deploy/examples/instance-overlays/` or instance Obsidian — not required in template vault

```bash
# Quick scan (should return no hits with real secrets)
rg -i 'pit-[a-f0-9]{20,}|sk-[a-zA-Z0-9]{20,}|Bearer [a-zA-Z0-9._-]{20,}' --glob '!*.example' --glob '!*.md' deploy/
```

---

## Instance overlay (reference VPS)

The live MCO/AVE/WNN multi-account setup belongs on the **reference VPS** only:

- `config/ghl-accounts.json` copied from `ghl-accounts.instance.rei.example.json`  
- PIT + location IDs in `/docker/clawsum/.env`  
- `obsidian/GHL/REI-GHL-AGENT-PLAYBOOK.md` copied from `deploy/examples/instance-overlays/`

Do not commit those instance files to the generic template remote.
