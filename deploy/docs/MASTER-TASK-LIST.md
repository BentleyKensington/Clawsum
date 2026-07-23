# Clawsum master task list

**Last updated:** 2026-07-02  
**Reference VPS:** `76.13.97.82` · `/docker/clawsum`

Two lists — do not mix them:

| List | What | Where |
|------|------|--------|
| **Boss work queue** | Business tasks (Gmail, CLA backlog) — needs *your* answers | Boss UI → CLA-41 + task comments |
| **Platform task list** | Infrastructure and product gaps — **this file** | Sections below |

**Roadmap detail:** [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) · **Template gate:** [PLATFORM-DEPLOY-TEMPLATE.md](./PLATFORM-DEPLOY-TEMPLATE.md)

---

## Naming (locked)

| Name | What it actually is |
|------|---------------------|
| **Boss UI** | **Paperclip** web app — company **Clawsum**, your task/approval surface. Not Hermes-branded. |
| **OpenClaw Control UI** | Gateway admin (channels, Gmail, devices) at `clawsum.${DOMAIN}` |
| **Clawsum Hermes** | A **Paperclip assignee** for long jobs — runs **headless** via `openclaw_gateway` → session `paperclip:hermes`. Not a separate product UI in our stack. |
| **Hermes Agent dashboard** | **Nous Hermes** product UI (`hermes dashboard`, port 9119) — **not deployed** on Clawsum today |

---

## ✅ Done (reference VPS)

### Tier 0 — platform shell
- [x] Docker Compose: postgres, arcadedb, openclaw-gateway, paperclip, monitoring
- [x] OpenClaw `2026.6.10` + multi-agent workspaces + persona seed
- [x] Paperclip ↔ OpenClaw protocol v4, pairing, adapters
- [x] Codex-first LLM policy (`enforce-llm-codex-first.py`)
- [x] Generic `ghl` agent template (REI → instance overlay)
- [x] Credentials scrubbed from repo; `.env` instance-only
- [x] `bootstrap-new-vps.sh`, `env.example`, `verify-platform.sh`

### Tier 1 — operational baseline
- [x] Gmail sync cron + triage scripts (cron off during Boss pause)
- [x] Daily report + Obsidian sync crons
- [x] Heartbeats pause/resume runbooks
- [x] Hermes policy: Boss-authorized only, heartbeat OFF, `openclaw_gateway` path
- [x] Boss UI HTTPS route (`setup-boss-ui-traefik.sh` / `boss.srv.example.com`)
- [x] Telegram smoke script (manual @mention sign-off pending)
- [x] GHL MCO REI live on instance (playbook in overlay)

### Tier 2 — proved on live VPS (2026-07-02)
- [x] **Redis** — healthy
- [x] **MinIO** — buckets + upload smoke
- [x] **LangGraph** — OSS runner, `/runs/wait` smoke passed
- [x] **Backups** — `backup-platform.sh` artifacts + MinIO upload
- [x] `verify-tier2.sh` + Tier 2 section in `verify-platform.sh` **PASSED**

### Repo / docs (recent)
- [x] OpenRouter escalation scaffold (`configure-openrouter-escalation.py`, `openrouter_client.py`)
- [x] On-demand STT/TTS (`speech_api.py`)
- [x] Ops portal docs + `setup-ops-portal-traefik.sh` (unified Traefik login)
- [x] `BOSS-OPS-PORTAL.md`, `OPENROUTER-AND-VOICE.md`

---

## 🔄 In progress / Boss-blocked

### Wave 1 — operational truth
- [ ] **Boss answers** on CLA-41 / per-task clarification comments
- [ ] **Resume heartbeats** after Boss approves (`paperclip-resume-work.py --enable-heartbeats`)
- [ ] **Gmail triage production** — re-enable cron after pause; wire to Paperclip tasks
- [ ] **Telegram smoke** — manual @mention in every group (incl. GHL)
- [ ] **Boss Obsidian desktop** — [BOSS-OBSIDIAN-WINDOWS.md](./BOSS-OBSIDIAN-WINDOWS.md)
- [ ] **Promote-to-Obsidian policy** — one paragraph in all agent SOUL/WORKFLOWS

### Git / template publish
- [ ] `git init` + first commit → `github.com/BentleyKensington/Clawsum`
- [ ] Confirm `git status` shows no secrets before push

---

## ⬜ Not done — platform backlog

### UIs & access
- [ ] **Ops portal live** — run `setup-ops-portal-traefik.sh` with real domain + DNS
- [ ] **OpenClaw trusted-proxy** — `patch-control-ui-trusted-proxy.py` after portal auth
- [ ] **Authelia / Cloudflare Access** — replace basic auth for production SSO (optional)
- [x] **Hermes dashboard on VPS** — installed v0.18.0; `http://127.0.0.1:9119` (SSH tunnel) or `hermes.*` after Traefik
- [x] **Hermes cockpit overlay (repo)** — `deploy/examples/hermes-cockpit` + `install-hermes-cockpit.sh` (theme, logo, Brief/Approvals/Grafana)
- [ ] **Hermes cockpit on VPS** — run install script + set `CLAWSUM_*` / Grafana embed URL
- [ ] **Hermes dashboard public URL** — DNS + `setup-ops-portal-traefik.sh` (**primary CEO browser face** — [CEO-COCKPIT.md](./CEO-COCKPIT.md))
- [ ] Grafana behind same Traefik auth (included in ops-portal script)
- [x] **Paperclip overwatch Phase 3 starter** — `12-overwatch.sql`, seed cells, approval scripts ([PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md))
- [x] **Daily report CRON_TZ fix** — 07:00 America/Chicago (was firing ~02:00 CDT on UTC VPS)

### LLM & routing
- [ ] **`OPENROUTER_API_KEY`** on VPS + run `configure-openrouter-escalation.py`
- [ ] **Model catalog env** — free/coding/frontier/multilingual slugs in `.env`
- [ ] **Task label convention** — `llm:default|cheap|frontier|coding` on Paperclip issues
- [ ] **NVIDIA NIM** — direct API key + base URL OR OpenRouter `:free` / Nemotron slugs
- [ ] **GLM / rising stars** — via OpenRouter (`z-ai/glm-4.5-air:free`, etc.)
- [ ] Wire `paperclip-analyze-assign-boss.py` to suggest `llm:*` labels — **done in analyze script**; agents reading labels still ⬜
- [ ] LangGraph graphs call real LLM (not stub nodes) when triage goes production

### Tier 2 — remaining automation spine
- [ ] **ArcadeDB ETL** — RE comps schema + `arcadedb-ingest.py` production
- [ ] **Grafana → Telegram** — wire `grafana-telegram-notifier.sh`
- [ ] **Platform crons** — `install-platform-crons.sh` on VPS
- [ ] **LangGraph** — production graphs wired to gmail-triage + research pipelines
- [ ] **Hostinger decommission** (Phase 8)

### Tier 3 — domain packs (per instance)
- [ ] Bright Data scrapers (Phase 5)
- [ ] GHL AVE/WNN accounts (await PIT)
- [ ] Comms / WhatsApp cutover
- [ ] Voice two-way (STT/TTS policy in admin + comms SOUL)
- [ ] 3D RE comp viewer
- [ ] Supabase / custom Boss portal (deferred)

### Template gate (before cloning VPS)
- [ ] Tier 1 gate: `verify-platform.sh` + Telegram smoke sign-off
- [ ] Tier 2 gate: all Tier 2 items above except deferred Tier 3
- [ ] Instance overlay docs per pack (GHL, RE)

---

## Hermes UI — your questions answered

### Is Hermes UI available the way we have it set up?

**No.** Nous shipped a **Hermes Agent web dashboard** (`hermes dashboard` → `http://127.0.0.1:9119`), but **Clawsum does not run it**.

Our production path (from `paperclip-fix-execution.py` + [HERMES-POLICY.md](./HERMES-POLICY.md)):

```text
Boss UI (Paperclip / Clawsum)
    → assignee: Clawsum Hermes
    → adapter: openclaw_gateway
    → session: paperclip:hermes (admin gateway session)
    → Codex / ChatGPT Plus
```

- **`hermes_local`** + `install-hermes-in-paperclip.sh` = legacy / optional — **not installed** on VPS
- **Hermes CLI** in Paperclip container: missing (expected)
- **Hermes dashboard (:9119)**: not started, not in Traefik, not in compose

**Where you manage Hermes today:** Boss UI task board (filter assignee **Clawsum Hermes**), task activity, Obsidian deliverables under `Paperclip/`.

### If you want Hermes dashboard later (optional overlay)

1. Install in Paperclip container: `install-hermes-in-paperclip.sh` + `pip install hermes-agent[web]`
2. Run `hermes dashboard` bound to `127.0.0.1:9119`
3. Add Traefik route `hermes.${DOMAIN}` with **same ops-portal auth** — never expose :9119 raw
4. Decide: keep **headless Paperclip slave** path (recommended) vs switch assignee to `hermes_local` (API billing, separate runtime)

**Recommendation:** Stay headless through Paperclip + OpenClaw unless you need Hermes-specific session/chat UI features Nous added in v0.16+.

---

## LLM routing — how the system should pick models

See [OPENROUTER-AND-VOICE.md](./OPENROUTER-AND-VOICE.md) + [LLM-ROUTING.md](./LLM-ROUTING.md).

**Principle:** GPT via **Codex subscription** for interactive agents; **OpenRouter** for everything that is *not* OpenAI/GPT; **never** route `openai/*` through OpenRouter.

| Trigger | Model path | Who decides |
|---------|------------|-------------|
| Telegram / OpenClaw chat | `openai/gpt-5.4` Codex → API fallback | Automatic (auth order) |
| Cron / batch (default) | `gpt-4o-mini` via `OPENAI_API_KEY` | Script default |
| Provider failure | OpenRouter fallbacks (Claude, Gemini, …) | OpenClaw automatic |
| Boss `/model` switch | Any catalog model | Boss manual |
| Paperclip label `llm:cheap` | OpenRouter `:free` or `:floor` (Nemotron, GLM Air, DeepSeek free) | Task metadata |
| Paperclip label `llm:frontier` | OpenRouter escalation (Claude Sonnet, Gemini Pro) | Task metadata |
| Paperclip label `llm:coding` | OpenRouter Qwen3 Coder / Devstral | Task metadata |
| Script flag `--escalate` | `openrouter_client.py` | Script caller |
| NVIDIA NIM direct | `NVIDIA_NIM_API_KEY` + build.nvidia.com OpenAI-compatible URL | Env (optional alongside OR) |

**Best implementation order:**
1. Add `OPENROUTER_API_KEY` + escalation models to `.env`
2. Adopt **Paperclip issue labels** (`llm:cheap`, `llm:frontier`, `llm:coding`) — agents read from task description
3. Extend `paperclip-analyze-assign-boss.py` to propose labels from task type
4. Keep **no auto-escalation to paid frontier** without label or Boss approval (cost control)

---

## Quick VPS commands

```bash
cd /docker/clawsum
python3 scripts/paperclip-task-status.py
bash scripts/verify-platform.sh
bash scripts/verify-tier2.sh

# After Boss approves work
python3 scripts/paperclip-resume-work.py --enable-heartbeats

# LLM + OpenRouter
python3 scripts/enforce-llm-codex-first.py

# Public ops portal (Boss + OpenClaw + Grafana)
bash scripts/setup-ops-portal-traefik.sh
```

---

## Related

- [SETUP-REMAINING.md](./SETUP-REMAINING.md) — pause/resume context, Boss UI errors
- [HERMES-POLICY.md](./HERMES-POLICY.md) — when to assign Hermes
- [BOSS-OPS-PORTAL.md](./BOSS-OPS-PORTAL.md) — public HTTPS + login wall
- [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) — full architecture
