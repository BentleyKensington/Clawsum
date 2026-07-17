# Clawsum platform deploy template

**Purpose:** One **complete, versioned system template** that can be cloned to **additional separate VPS instances** for unrelated use cases. Each new VPS gets the same platform; **instance-specific config** (domains, credentials, optional domain packs) is applied at deploy time — not baked into the template repo as secrets.

**Gate:** Do **not** deploy additional production VPS instances until **Tier 0 + Tier 1 + Tier 2** below are **template-complete** on the reference stack (`srv.example.com`). Tier 3 is optional per instance.

**Reference stack:** `/docker/clawsum` on `YOUR_VPS_IP`  
**Related:** [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) · [SETUP-REMAINING.md](./SETUP-REMAINING.md) · [VERSION-PINNING.md](./VERSION-PINNING.md)

---

## Generic, unbranded template (doctrine)

The **repo template** must stay **generic** — no Boss brand, no market name, no REI-specific GHL accounts baked in. The reference VPS (`srv.example.com`) is an **instance** that added customization; that customization must **not** ship as the default clone.

| Layer | Template (repo) | Instance (e.g. Clawsum REI on srv.example.com) |
|-------|-----------------|---------------------------------------------|
| GHL agents | **One** `ghl` agent + optional `ghl-template` sandbox | Multi-account `ghl-mco-rei`, `ghl-ave-rei`, … via `config/ghl-accounts.json` |
| GHL config | `ghl-accounts.json` with **`accounts: []`** or one anonymous placeholder | MCO/AVE/WNN PITs, Telegram IDs, REI playbooks |
| Personas / SOUL | Domain-generic (“GHL CRM operator”) | REI seller language, landline tags, market names |
| Obsidian | Folder **structure** only (`GHL/`, `Admin/`, …) | `MCO-REI/`, `REI-GHL-AGENT-PLAYBOOK.md`, audit data |
| Scripts | Generic `--slug` / `--location-id` flags | Hard-coded `mco-rei` defaults removed from template |
| Paperclip names | `Clawsum GHL` (one agent) | `Clawsum GHL — MCO REI`, etc. |

**Original plan** ([IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md)): one `ghl` workspace, one Telegram group, one `ghl` Postgres DB — not three branded REI sub-agents.

### Template refactor (generic clone — done in repo)

- [x] Default roster: **single `ghl`** in `configure-openclaw.py` / `seed-persona-os.sh`
- [x] `ghl-accounts.json` — one generic `ghl` account; multi-account via `ghl-accounts.instance.rei.example.json`
- [x] `templates/ghl/` — generic CRM placeholders (`{DISPLAY_NAME}`, etc.)
- [x] `REI-GHL-AGENT-PLAYBOOK.md` → `deploy/examples/instance-overlays/` (gitignored in `obsidian/`)
- [x] Unbranded `ghl_accounts.py` delegation (needles from config, not hard-coded MCO/AVE/WNN)
- [x] `.gitignore` + [CREDENTIALS-EXCLUSION.md](./CREDENTIALS-EXCLUSION.md)
- [x] [AI-PERSONA-OS.md](./AI-PERSONA-OS.md) + `templates/persona/MANIFEST.md`
- [x] Remove REI-specific defaults from strategic audit (`--vertical rei` for instance overlay)

---

```text
┌─────────────────────────────────────────────────────────────┐
│  CLAWSUM TEMPLATE (repo: deploy/, scripts/, templates/)      │
│  Same on every VPS — no Boss secrets, no business data       │
└──────────────────────────────┬──────────────────────────────┘
                               │ bootstrap-new-vps.sh
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  INSTANCE OVERLAY (per VPS — never committed)                │
│  .env · Traefik hostnames · Telegram group IDs · GHL PITs    │
│  Optional: enable GHL pack, RE pack, scrapers, extra agents  │
└─────────────────────────────────────────────────────────────┘
```

| Layer | In template repo | Per instance at deploy |
|-------|------------------|------------------------|
| `docker-compose.yml`, profiles | Yes | Host-specific ports/domains only |
| Postgres init SQL | Yes | DB passwords in `.env` |
| Agent personas (`templates/`, seed scripts) | Yes | — |
| Obsidian **structure** + runbooks | Yes | Vault **content** grows per instance |
| Scripts (audit, triage, provision) | Yes | — |
| GHL | **One generic `ghl` agent** + provision **pattern** for extra accounts | PIT, locationId, optional multi-account JSON |
| Boss email, OAuth tokens, API keys | **Never** | `.env` only |
| Paperclip tasks / CRM data | **Never** | Instance data volumes |

---

## LLM policy (template)

| Path | Provider | When |
|------|----------|------|
| **OpenClaw agents (Telegram)** | **ChatGPT Plus via Codex OAuth** (`openai-codex`) | Primary — subscription billing |
| **OpenClaw fallback** | `OPENAI_API_KEY` → `openai:default` | When Codex OAuth missing/expired |
| **Default model** | `openai/gpt-5.4` (via `enforce-llm-codex-first.py`) | Agent turns |
| **Crons / batch scripts** | `OPENAI_API_KEY` → **`gpt-4o-mini`** | `gmail-triage.py`, `ghl-strategic-audit.py --use-llm` |
| **Cron escalation (non-GPT)** | `OPENROUTER_API_KEY` → `openrouter_client.py` | Claude/Gemini/etc. only |
| **OpenRouter (agents)** | `openrouter/<author>/<model>` fallbacks | When GPT path fails or Boss `/model` switch |
| **Speech STT/TTS** | `speech_api.py` + OpenClaw `/tts` | On demand — `SPEECH_*_PROVIDER` in `.env` |
| **OpenRouter for OpenAI models** | **Not used** | GPT stays on Codex / direct API |
| **Anthropic direct** | Optional in `.env` | **Not used** — use OpenRouter `anthropic/*` instead |

OpenRouter and speech setup: [OPENROUTER-AND-VOICE.md](./OPENROUTER-AND-VOICE.md). Run `configure-openrouter-escalation.py` after adding `OPENROUTER_API_KEY`.

See [OPENAI-AUTH.md](./OPENAI-AUTH.md), [BOSS-ACCESS-GUIDE.md](./BOSS-ACCESS-GUIDE.md) § LLM billing.

---

## Original plan — what remains

From [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md) phases + [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md):

| Area | Remaining |
|------|-----------|
| **Template genericity** | Single `ghl` agent; unbrand repo; move REI/MCO customizations to instance overlay |
| **Tier 2** | MinIO, LangGraph (+ graphs), ArcadeDB ETL, Grafana→Telegram, backups |
| **Tier 1** | Gmail triage production, Telegram smoke sign-off, Obsidian promotion policy |
| **Phase 5** | Bright Data scrapers |
| **Phase 6** | Self-healing / alert automation |
| **Phase 8** | Hostinger disk decommission |
| **Deferred** | Supabase, voice, 3D viewer |
| **OpenRouter / LLM tiers** | Scaffold in repo — [LLM-ROUTING.md](./LLM-ROUTING.md); needs VPS keys |
| **Instance-only** | MCO multi-GHL, REI audit tuning, CLA backlog — stays on reference VPS |

---

## Completion tiers (all required before multi-VPS)

### Tier 0 — Platform shell ✅ mostly done

Bare metal → running gateway + Postgres + Paperclip skeleton.

| Item | Status | Notes |
|------|--------|-------|
| Docker Compose (postgres, arcadedb, openclaw-gateway, paperclip, monitoring) | ✅ | Profiles: `orchestration`, `monitoring` |
| Postgres init (clawsum, realestate, ghl schemas) | ✅ | `postgres-init/` |
| OpenClaw multi-agent workspaces + persona seed | ✅ | `seed-persona-os.sh`, `configure-openclaw.py` |
| Obsidian vault scaffold | ✅ | `setup-obsidian-vault.py` |
| Traefik + Control UI HTTPS | ✅ | Clawsum + Boss UI routes |
| Version pins + upgrade script | ✅ | OpenClaw `2026.6.10`, Paperclip `latest` + digest |
| **Greenfield bootstrap script** | ✅ | `scripts/bootstrap-new-vps.sh` |
| **Master env.example** | ✅ | `deploy/env.example` |
| Remove Hostinger-only paths from default docs | 🔄 | `setup-migrate.sh` stays for legacy; bootstrap is canonical |

**Tier 0 gate:** Fresh VPS → `bootstrap-new-vps.sh` → healthz OK, Boss UI loads, **9 core agents + 1 `ghl`** (not 12 branded).

---

### Tier 1 — Operational truth 🔄 in progress

Daily-usable ops without manual VPS surgery.

| Item | Status | Blocker for clone? |
|------|--------|-------------------|
| Paperclip ↔ OpenClaw (protocol v4, pairing, adapters) | ✅ | — |
| Telegram bindings (9 core groups + GHL MCO) | 🔄 | Manual @mention smoke on all groups |
| Gmail sync cron | ✅ | — |
| Gmail **intelligent triage** (classify → Postgres → optional Paperclip) | 🔄 | Policy + cron off during Boss pause |
| Daily report + Obsidian sync crons | ✅ | — |
| Admin daily playbook | ✅ | `Admin-Runbooks/daily-boss-routine.md` |
| Boss UI HTTPS | ✅ | — |
| Heartbeats pause/resume runbooks | ✅ | — |
| Telegram + platform smoke scripts | ✅ | `telegram-smoke-test.sh` |
| **Promote-to-Obsidian policy** in all agent SOUL/WORKFLOWS | ⬜ | Standardize one paragraph + checklist |
| **Instance verify script** (single `verify-platform.sh`) | ⬜ | Wraps smoke + isolation + crons |

**Tier 1 gate:** Reference VPS passes `verify-platform.sh`; Boss can read reports in Obsidian + Boss UI without SSH hacks.

---

### Tier 2 — Automation spine ⬜ not template-complete

Required so a cloned VPS is not a “chat-only” stack — automation and knowledge pipelines work out of the box.

| Item | Status | Blocker for clone? |
|------|--------|-------------------|
| **MinIO** (compose profile `storage`) | ✅ live on reference VPS | — |
| **LangGraph** service running + health | ✅ OSS runner | Wire graphs to production LLM |
| **`gmail_triage` graph** | 🔄 | Stub node; script exists |
| **`research_brief` graph** | 🔄 | Stub node |
| **ArcadeDB schema + ingest** | ⬜ | Container only; `arcadedb-ingest.py` unused |
| **Grafana → Telegram alerts** | ⬜ | Rules exist; notifier not wired |
| **GHL domain pack** | ✅ | Single generic `ghl` agent in template |
| **REI GHL playbook** | ✅ | Instance overlay example only |
| **Backup cron** (pg_dump + Obsidian → MinIO) | ✅ | `backup-platform.sh` proved on VPS |
| Hostinger decommission / no legacy references | 🔄 | Phase 8 cleanup |

**Tier 2 gate:** LangGraph triage runs on schedule; MinIO buckets created by bootstrap; ArcadeDB accepts test ingest; alerts reach Admin Telegram.

---

### Tier 3 — Domain packs (optional per instance)

Enable only what that VPS needs. Template ships **patterns**, not live credentials.

| Pack | Template artifacts | Instance config |
|------|-------------------|-----------------|
| **GHL** | One `ghl` agent, `templates/ghl/`, audit scripts with generic flags | PIT, locationId; optional extra accounts in `ghl-accounts.json` |
| **Real estate** | `realestate` DB schema, Obsidian `RealEstate/` | Market-specific data |
| **Bright Data scrapers** | LangGraph `scrape_validate_store` (TBD) | API keys |
| **Comms / WhatsApp** | comms agent persona | Plugin + cutover policy |
| **Supabase / Boss portal** | Deferred | Path B/C decision |

---

## What blocks deploying additional VPS **today**

1. **No Tier 2** — LangGraph, MinIO, ArcadeDB ETL, alert notifier not built  
2. **Tier 1 gaps** — Gmail triage not production; full Telegram smoke not signed off  
3. **No single verify gate** — scripts exist piecemeal; need `verify-platform.sh`  
4. **Bootstrap was migration-centric** — greenfield path now documented but Tier 2 services not in bootstrap yet  
5. **Instance overlay docs** — need per-pack config checklists (GHL, RE, etc.)

**Allowed now:** Dev/staging VPS for testing bootstrap (Tier 0). **Not allowed:** Production clone for unrelated business until Tier 1 + Tier 2 gates pass on reference stack.

---

## Greenfield bootstrap (new VPS)

```bash
# 1. On fresh Ubuntu VPS with Docker
git clone <repo> /docker/clawsum   # or rsync deploy bundle
cd /docker/clawsum

# 2. Instance overlay
cp deploy/env.example .env
# Edit: secrets, TRAEFIK_HOST, tokens, optional GHL_* lines

# 3. Bootstrap (Tier 0 + Tier 1 scripts)
bash deploy/scripts/bootstrap-new-vps.sh

# 4. Optional domain packs (after credentials in .env)
bash deploy/scripts/provision-ghl-accounts.sh   # GHL pack
python3 deploy/scripts/verify-ghl-isolation.py

# 5. Telegram: add bot to groups, then
python3 deploy/scripts/bind-ghl-telegram.py --from-sessions   # GHL accounts
bash deploy/scripts/telegram-smoke-test.sh
```

Legacy Hostinger migration: `deploy/setup-migrate.sh` — **not** used for new unrelated VPS.

---

## Instance configuration checklist (copy per deploy)

```markdown
## VPS: _______________  Purpose: _______________  Date: ___________

### Core
- [ ] `.env` filled from env.example
- [ ] TRAEFIK_HOST / TLS certs
- [ ] OPENCLAW_GATEWAY_TOKEN rotated
- [ ] Paperclip BETTER_AUTH_SECRET, JWT secret
- [ ] bootstrap-new-vps.sh exit 0
- [ ] verify-platform.sh exit 0

### Telegram
- [ ] @YourTelegramBot added to each group
- [ ] Bindings applied (admin, coding, data, …)
- [ ] Manual @mention smoke passed

### Optional: GHL pack
- [ ] ghl-accounts.json edited for this instance's accounts
- [ ] PIT + locationId per account in .env
- [ ] provision-ghl-accounts.sh + verify-ghl-isolation.py
- [ ] First strategic audit per account

### Optional: Gmail
- [ ] OAuth + gmail-sync cron
- [ ] Triage policy agreed; install-gmail-triage-cron.sh

### Optional: Monitoring
- [ ] Grafana admin password
- [ ] Alert notifier → Admin Telegram
```

---

## Recommended finish order (reference VPS)

Complete on **srv.example.com** before cloning:

| # | Work | Tier | Est. |
|---|------|------|------|
| 1 | `verify-platform.sh` (wrap existing checks) | 1 | 1 day |
| 2 | Gmail triage production policy + cron | 1 | 2–3 days |
| 3 | Telegram full smoke sign-off | 1 | 1 day (Boss) |
| 4 | MinIO compose profile + buckets + env | 2 | 2 days |
| 5 | LangGraph deploy + `gmail_triage` graph | 2 | 1 week |
| 6 | ArcadeDB RE comp schema + ingest path | 2 | 1 week |
| 7 | Grafana → Telegram notifier | 2 | 2 days |
| 8 | Backup cron → MinIO | 2 | 1 day |
| 9 | Update bootstrap for Tier 2 services | 2 | 1 day |
| 10 | **Template sign-off** — run bootstrap on clean VM | 0–2 | 2 days |
| 11 | Hostinger decommission | 2 | 1 day |

**After #10:** Additional VPS for unrelated use cases is approved.

---

## Repository layout (template surface)

```text
deploy/
  docker-compose.yml          # Core + profiles (orchestration, monitoring, storage TBD)
  env.example                 # Master instance overlay template
  env.ghl.example             # GHL pack add-on
  env.gmail.example           # Gmail pack add-on
  config/ghl-accounts.json    # GHL account registry (edit per instance)
  templates/ghl-account/      # Per-account agent template
  postgres-init/              # DB schema (all instances)
  scripts/
    bootstrap-new-vps.sh      # Greenfield install
    upgrade-platform-versions.sh
    verify-platform.sh        # (TBD) Single gate
    provision-ghl-accounts.py
    ghl-strategic-audit.py
  docs/
    PLATFORM-DEPLOY-TEMPLATE.md   ← this file
    REI-GHL-AGENT-PLAYBOOK.md     ← obsidian/GHL/
obsidian/                     # Vault structure (synced to VPS)
```

---

## Version policy (template)

Pin in `docker-compose.yml` + document in [VERSION-PINNING.md](./VERSION-PINNING.md). After any bump on reference VPS:

1. Run `upgrade-platform-versions.sh`
2. Run `verify-platform.sh` (when exists)
3. Update VERSION-PINNING.md digest lines
4. Tag repo release (optional) before cloning to new VPS

---

## Related domain templates

| Domain | Template doc |
|--------|----------------|
| GHL (instance overlay) | [GHL-MULTI-ACCOUNT-PLAN.md](./GHL-MULTI-ACCOUNT-PLAN.md) — **multi-account is instance pattern, not template default** |
| Agent capabilities | [GHL-AGENT-CAPABILITIES.md](./GHL-AGENT-CAPABILITIES.md) |

---

*Last updated: 2026-07-01 — Template gate: Tier 2 incomplete; do not clone to additional production VPS until Tier 1 + Tier 2 sign-off.*
