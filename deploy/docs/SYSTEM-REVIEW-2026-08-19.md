# Clawsum high-level system review — 2026-08-19

**VPS:** `76.13.97.82` · `/docker/clawsum`  
**Repo:** local Windows workspace (this sprint)  
**Prior status:** [STATUS-REPORT-2026-08-06.md](./STATUS-REPORT-2026-08-06.md)

This is an architecture and ops review, not a dump of every script.

---

## What Clawsum is

Three planes:

1. **Boss face** — Hermes cockpit / Discord / Telegram. Clarifies, links, asks. Does not own prod mutates.
2. **Board** — Paperclip (`127.0.0.1:3100`, public Authelia; agents use host proxy `:3102`).
3. **Hands** — OpenClaw gateway agents with per-workspace SOUL + skills on disk.

Shared truth: **Postgres** (ops + domain DBs) · **ArcadeDB** (graph mirror) · **Obsidian** (durable notes) · **MinIO** (blobs).

**Rule that is working:** 1 domain = 1 agent = 1 workspace. Skills are tools. Products and liability get agents.

---

## Health snapshot (from repo + last VPS report)

| Plane | State | Gap |
|-------|-------|-----|
| Docker compose (gateway, postgres, arcade, paperclip, grafana) | Live on VPS (Aug 6) | Local twin deferred |
| Discord / Telegram | Recovered; outage replay armed | Telegram history still cannot replay |
| Paperclip agent closeout | Fixed via `:3102` | Agents must never hit public hostname |
| Gmail archive | Scripts + schema exist | Triage cron was paused; confirm before enable |
| Memory Phase 1–2 | Designed + scripts | Confirm crons actually firing on VPS |
| ChatGPT archive | Import/classify/link/promote exist | Promote is Boss-gated; not a silent dump |
| Media studio | Agent + Phase 0 | Ingest `--apply`, Whisper URL, publish OAuth |
| Product agents (CloseBot, Printful, Shopify, AcceptAI) | Persona + Discord lanes | **Missing from `configure-openclaw.py` and Paperclip wire** — re-running configure would drop them |
| `llm-lab` | Cockpit Team tile only | No OpenClaw workspace until this sprint |
| Heartbeats | Off | CLA-41 / RESUME-POLICY |

---

## Hermes / OpenClaw / Paperclip — upgrade advice

### OpenClaw (gateway)

| Channel | Version | Use |
|---------|---------|-----|
| **Pinned now** | `2026.6.10` | What compose + `.env` say |
| **Safest bump** | `2026.6.34` extended-stable | Same 2026.6 line; GHCR `latest` currently tracks this line, not 2026.7 |
| **Next stable** | `2026.7.1-2` (explicit tag) | Control UI, GPT-5.6, browser/remote, Codex attach. Pin the **`-2`** rebuild, never `:latest` |
| **Avoid on prod** | `2026.8.1-beta.*` | Secret-egress + snapshot work is attractive but beta |

**Do this:** snapshot `.openclaw` + `paperclip-data` → bump OpenClaw first → Telegram/Discord smoke → one gateway agent call → only then Paperclip image.

**Why not jump 6.10 → 8.x:** two major lines (7 then 8-beta), known `:latest` tag races, and heartbeats still off. Pay the 6.34 or 7.1-2 tax in a maintenance window.

### Hermes Agent (Nous)

| Mode | Advice |
|------|--------|
| **Production path** | Keep **headless**: Paperclip assignee Clawsum Hermes → `openclaw_gateway` → Codex |
| **Dashboard** | Docs said v0.18.0 optional on VPS `:9119`. Upstream latest **v0.20.4** (2026.8.18) |
| **Upgrade dashboard?** | Yes *if* you already run it and want cockpit plugins to keep working — test on a copy. Do **not** switch execution to `hermes_local` (API billing, second runtime) |
| **Separate Hermes app?** | No. Cockpit is a skin. Execution stays OpenClaw |

### Paperclip

Stay on digest-pinned `latest` until GHCR version tags are trustworthy. Re-run protocol v4 patch after any image pull.

### Separate apps vs more agents

| Keep as **skill** | Promote to **agent** (this sprint) |
|-------------------|--------------------------------------|
| Scraper, OSINT, Graphify, Photos Picker, vendor HTTP helpers | Vocalitic, AcceptAI (product), VAPI, SellTheBizFast, Rocco, LLM Lab |
| Deep research browser | — (Research + LLM Lab share the skill) |

Do **not** spawn a company per SaaS. CloseBot / Printful / Shopify are already the right split (own brand + API + Discord lane). Finish wiring them; don’t invent a fourth commerce orchestrator.

---

## Memory, databases, dreaming, ChatGPT history

### Data stores

| Store | Role | Daily population |
|-------|------|------------------|
| `ops.memory_facts` | Typed triples, `active` / `historical` | Immediate extract + archive promote |
| `ops.memory_episodes` | Experiences | Same |
| `ops.memory_dream_runs` | Job log | Hourly / nightly / weekly |
| Arcade `Fact` / `Episode` / `MemoryEntity` | Graph mirror + `Supersedes` | After Postgres write |
| Obsidian `Admin/Memory/*-dream.md` | Human-readable compress | Nightly 02:15 Chicago |
| `Admin/Self-Model.md` | Weekly identity | Sunday 03:30 |
| `ops.conversations` + messages | ChatGPT import | Only when a new export is copied to VPS |
| `ops.emails` | Gmail archive | Sync cron every 15 min (7 ingested today) |
| Domain DBs `ghl` / `realestate` | Isolated | Cell agents only |

### Dreaming — is it effective?

**Design is sound:** expire / dedupe / contradict hourly; LLM-compress hot subjects nightly; deeper weekly self-model. That is the right shape for a CEO assistant that must not drown in chat.

- **4947** active facts / **489** historical (dreaming is historizing).
- Hourly dream last ran **2026-08-19 21:20 UTC** (living).
- Nightly last ran **2026-08-19 07:19 UTC** (~02:19 Chicago — today's compress ran).
- Weekly last ran **2026-08-16** (Sunday window).
- ChatGPT archive: **2239** conversations, **1816** `approved_for_hermes` — the archive **is** being referenced/promoted, not sitting idle.
- Gmail: **7** messages ingested today; pipeline cron every 15 minutes is **on**. Deepgram scan uses `from_addr` (not `from_address`).

**Verdict:** dreaming is living and compressing. Next quality check is whether nightly notes in `Admin/Memory` are useful to Gerald, not whether jobs fire.

### Is ChatGPT history referenced?

**Yes, in production:** **2239** conversations imported; **1816** marked `approved_for_hermes`. Inbox/task analysis consults `ops.conversations` (skips personal). Promote to `ops.memory_facts` is gated and has clearly run at scale.

If agents still sound amnesiac, the usual causes are: Hermes not calling `archive-proactive-brief.py` this turn, or the fact is in historical status after a dream.

---

## Interview until the spec is crisp

Hermes already has `hermes-proactive-drive` (one question per blocked item). This sprint adds **`spec-interview`**:

1. Restate the ask in one sentence.
2. Fill a spec card: Goal · Success metric · Out of scope · Owner agent · Cell · Deadline · Risk tier · Dependencies · Open questions.
3. Ask **one** missing field at a time (highest-leverage first).
4. When the card is complete, open/update a Paperclip issue and stop. No silent execution of Tier 2+.

This is how Clawsum should behave on Vocalitic, AcceptAI, acquisitions, and Ring — **interview, then ticket**, not “build the whole company in one turn.”

---

## Gmail + task linking (items of interest)

Scripts already classify mail into cells (Vocalitic, CloseBot, AcceptAI, GHL, etc.). This sprint adds an explicit **link pass**: same sender/thread/keywords → existing `CLA-*` + archive conversations.

**Deepgram mail today:** attachments are **not** in this Cursor workspace. Next step on VPS: query `ops.emails` for `deepgram` since local midnight Chicago. Until that runs, Deepgram guidance uses public Flux/Nova/Aura docs (see [DEEPGRAM-AND-VOICE-STACK.md](./DEEPGRAM-AND-VOICE-STACK.md)).

---

## Skills and data sources we should add (beyond this sprint)

| Source | Why | How |
|--------|-----|-----|
| OpenClaw **browser** | Docs, SERP, vendor dashboards (read) | Already allowed on research/coding/media; teach agents to use it before `escalate` |
| Google Photos **Picker** | Printful mockups, media stills | Human picks; no full-library API (Google removed it Mar 2025) |
| GSC / GMB | SEO agent is a shell | OAuth later |
| Printful + Shopify Admin APIs | Agents exist but are notes-only | Keys in `.env` |
| VAPI + CloseBot APIs | Voice + closer stack | This sprint |
| Ring **Appstore** official API | Rocco cameras | Private Use Apps, max 5 accounts |
| NVIDIA NIM + OpenRouter `:free` | Cheap/free quality | LLM Lab weekly watch |
| Deepgram Flux | Voice-agent STT/TTS | Eval vs ElevenLabs |
| ChatGPT archive (already) | Intent + questions | Keep gated promote |
| v1m12 / AcceptAI git over SSH | Product agents that can *see* the app | Read-only by default; mutate = T2 |

---

## Vocalitic / AcceptAI / CloseBot / VAPI / commerce — current vs target

| Agent | Today | Target |
|-------|-------|--------|
| Vocalitic | Cell + `vocalitic-health` on **coding** | Dedicated product agent; codebase + SSH; dashboard observations → approval |
| AcceptAI | Thin SOUL + FastBuy skill on **comms** | Product agent like Vocalitic |
| CloseBot | Discord + persona; skill lived on VPS Hermes tree | Repo skill + agency API; send = T2 |
| VAPI | Mentioned in GHL account fields | Own agent + `VAPI_API_KEY` |
| Printful / Shopify | Discord lanes; no API skills | API ops + Photos Picker for art |
| SellTheBizFast | Missing | New acquisition agent |
| Rocco | Missing (pentest exists) | Sentry + official Ring; pentest stays scans |

---

## Rocco / Ring — hard boundary

The Reddit “reverse engineered my Ring doorbell” path is **out of scope**. Ring now has an official **Appstore API** (`https://api.amazonvision.com`) plus **Private Use Apps** (allowlist up to 5 Ring accounts, no public listing). That is how Rocco will talk to *your* cameras.

Rocco will **not** ship unofficial protocol RE, credential stuffing, or exploit PoCs. 24/7 recording and a desktop live window are Phase 2 **after** official OAuth + media endpoints work.

---

## Cost doctrine (LLM Lab)

Default: Codex Plus for interactive; `gpt-4o-mini` or OpenRouter `:free` for batch. Paid Claude/Gemini Pro only when:

- Paperclip line `llm:frontier` / `llm:research`, or
- Boss writes standalone **`escalate`**, or
- Primary provider errors (automatic fallback — not “this feels hard”).

Weekly watch exists so we *change the cheap roster* when NVIDIA/Deepgram/OpenRouter free models move — not so we silently spend.
