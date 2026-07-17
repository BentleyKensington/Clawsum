# Clawsum Platform — Master Architecture Report

**Server:** `srv.example.com` (`YOUR_VPS_IP`) · **Stack path:** `/docker/clawsum`  
**Date:** 2026-05-23  
**Audience:** Boss (the operator) — how the system is built today, how it should work, and what to build next.

---

## Executive summary

Clawsum is a **multi-layer operations platform**: nine **OpenClaw** specialist agents (plus a **Paperclip** liaison agent), **Paperclip** for task orchestration, **Hermes** for long jobs, knowledge stores (Postgres, Obsidian, ArcadeDB), optional **object storage (MinIO)**, and ops surfaces (Telegram, Boss UI, OpenClaw Control UI, Grafana). **Self-hosted Supabase** is optional and should not replace Postgres until there is a clear need for a custom Boss portal with auth/realtime.

**Your understanding is correct at the design level:** agents should use **Postgres** for structured data, **Obsidian** for durable human-readable knowledge, and **ArcadeDB** for relationships and vectors. **That triad is only partly implemented.** Today Postgres + Obsidian vault scaffolding + cron are live; **ArcadeDB is empty**, **Gmail is archived but not intelligently processed**, and **LangGraph is a compose placeholder only**.

**Boss (you)** should **read and steer** Obsidian (especially `Admin/`), not micromanage every agent folder. Agents **write** their own vault folders; admin **routes** cross-domain work via Paperclip and Telegram.

---

## 1. Target knowledge model (design intent)

```text
                    ┌─────────────────────────────────────┐
                    │              BOSS (the operator)           │
                    │  Telegram · Boss UI · Obsidian read   │
                    └──────────────┬────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   ┌───────────┐            ┌────────────┐            ┌────────────┐
   │ Paperclip │◄──────────►│  OpenClaw  │            │   Hermes   │
   │ Boss UI   │  heartbeats│ 9+1 agents │            │ long jobs  │
   └─────┬─────┘            └──────┬─────┘            └─────┬──────┘
         │                         │                         │
         └────────────┬────────────┴────────────┬────────────┘
                      ▼                         ▼
              ┌───────────────┐         ┌───────────────┐
              │   PostgreSQL   │         │   Obsidian    │
              │  system of     │         │  vault (per-  │
              │  record (SQL)  │         │  agent notes) │
              └───────┬───────┘         └───────┬───────┘
                      │                         │
                      └──────────┬──────────────┘
                                 ▼
                        ┌───────────────┐
                        │   ArcadeDB    │
                        │ graph + vector│
                        └───────────────┘
```

### Three stores — who uses what

| Store | Purpose | Who writes | Who reads |
|-------|---------|------------|-----------|
| **PostgreSQL** | Canonical rows: emails, CRM, deals, ETL, reminders, task links | `data`, domain agents, crons | All agents (within policy), reports, LangGraph |
| **Obsidian** | Durable notes: briefs, ADRs, runbooks, triage summaries, promoted knowledge | Each agent → **own folder**; admin → `Admin/` | **Boss** (full vault), agents (their folder + policy) |
| **ArcadeDB** | Graph edges, RAG chunks, comp similarity, citation networks | `data`, `research`, `realestate` (when built) | Research, RE, cross-domain via approved graph |

### OpenClaw session memory (fourth layer — not Obsidian)

Each agent also has **`workspace-<agent>/memory/YYYY-MM-DD.md`** — short-lived **session context** for the model. Rule:

| Layer | Lifespan | Content |
|-------|----------|---------|
| `memory/` | Days / sessions | What happened today in chat |
| `notes/` | Scratch | WIP before promotion |
| **Obsidian** | Permanent | What Boss and future agents must retain |
| **Postgres** | Permanent | Queryable facts and pipeline state |

**Hermes** does not have a separate OpenClaw workspace on disk. Long-job **outputs** should land in:

1. **Paperclip task** description / comments (operational truth for work)
2. **`obsidian/Paperclip/`** or the **assignee agent’s folder** (durable artifact)
3. **Postgres** if the job produces structured rows (ETL, scrape results)

---

## 2. Should Boss access and manage Obsidian?

**Yes — read widely; write mainly in `Admin/`.**

| Boss activity | Where | How |
|---------------|-------|-----|
| Read daily platform health | `Admin/Reports/` | Auto-synced from 7am cron |
| Read agent deliverables | `Coding/`, `Research/`, etc. | Open vault on PC (git / Syncthing / SSHFS) |
| Triage Gmail narrative | `Admin/Inbox/` (target) | After intelligent triage pipeline |
| Set priorities / ADRs | `Planning/` or `Admin/Decisions/` | You or planning agent |
| Edit specialist domain notes | `RealEstate/`, `GHL/`, … | **Avoid** unless you are overriding — prefer Paperclip tasks |

Agents should **not** rely on Boss editing their folders. Boss **manages the system** via:

- **Boss UI (Paperclip)** — tasks, approvals, budgets, heartbeats
- **Telegram** — admin DM + CS Ops group
- **Obsidian** — strategic knowledge and reports, not replacing Paperclip task state

See [OBSIDIAN-VAULT.md](./OBSIDIAN-VAULT.md) for paths and sync.

---

## 3. Agent roster (10 workers in Paperclip)

| # | Paperclip name | OpenClaw id | Telegram | Postgres | Obsidian folder | Notes |
|---|----------------|-------------|----------|----------|-----------------|-------|
| 1 | Clawsum Admin | `admin` | DM + Ops | `clawsum.ops` | `Admin/` | Routes; no domain DB ownership |
| 2 | Clawsum Coding | `coding` | Coding group | `clawsum.coding` | `Coding/` | |
| 3 | Clawsum Data | `data` | Data group | `clawsum.data` | `Data/` | ETL, scrapers, LangGraph trigger |
| 4 | Clawsum RE | `realestate` | RE group | **DB `realestate`** | `RealEstate/` | Isolated DB |
| 5 | Clawsum GHL | `ghl` | GHL group | **DB `ghl`** | `GHL/` | Isolated DB |
| 6 | Clawsum Comms | `comms` | Comms group | `clawsum.comms` | `Comms/` | WhatsApp (cutover TBD) |
| 7 | Clawsum Research | `research` | Research group | `clawsum.research` | `Research/` | |
| 8 | Clawsum Planning | `planning` | Planning group | `clawsum.planning` | `Planning/` | |
| 9 | Clawsum Paperclip | `paperclip` | Paperclip group | — | `Paperclip/` | Orchestration liaison |
| 10 | Clawsum Hermes | **`hermes_local`** | — | — | `Paperclip/` or assignee | **Not** an OpenClaw Telegram agent; Paperclip adapter |

**Cross-domain rule (locked):** RE and GHL never query each other’s Postgres. Crossover via **Paperclip tasks**, **data ETL**, or **Boss-approved** ArcadeDB graph — not shared `MEMORY.md`.

---

## 4. What is live today (verified on VPS)

| Component | Status | Access |
|-----------|--------|--------|
| **OpenClaw 2026.6.10** | ✅ Running `:48166` | https://clawsum.srv.example.com/ + gateway token |
| **Telegram @YourTelegramBot** | ✅ On **Clawsum** (Hostinger container **stopped**) | 9 group bindings |
| **Paperclip / Boss UI** | ✅ `:3100` loopback | SSH tunnel; public domain doc ready, not applied |
| **Postgres** | ✅ `clawsum`, `realestate`, `ghl` | `127.0.0.1:5432` |
| **`ops.emails`** | ✅ ~80 rows, all **`pending`** | Gmail sync cron */15 |
| **`ops.reminders`** | ✅ Schema | 7:05 cron |
| **Gmail OAuth + gog** | ✅ Control UI Gmail | Separate from cron sync |
| **Obsidian vault** | ✅ 19 `.md` files, per-agent `OBSIDIAN.md` | `/docker/clawsum/obsidian` |
| **ArcadeDB** | ✅ Container only | **No schemas / no ETL** |
| **LangGraph** | ⬜ Compose service, **not running** | Profile `orchestration`; port 8123 |
| **Prometheus + Grafana** | ✅ Monitoring profile | SSH `:9090` / `:3000` |
| **Hermes CLI** | 🔄 Installed in Paperclip container | Re-run after image upgrades |
| **Traefik** | ✅ `:443` OpenClaw | Boss UI route pending |
| **Voice / 3D viz** | ⬜ Not started | — |
| **Hostinger cutover cleanup** | 🔄 Telegram cut over; `/docker/openclaw-qpr7` still on disk | Phase 8 |

### Cron timeline (America/Chicago)

| Time | Job |
|------|-----|
| */15 | `gmail-sync.py` → Postgres only |
| 7:00 | `daily-global-report.py` → Telegram + `data/reports/global-*.md` |
| 7:02 | Obsidian report sync → `Admin/Reports/` |
| 7:05 | `reminders-notify.py` |

---

## 5. AI Persona OS (per agent)

Seeded under each `workspace-<agent>/`:

| File | Role |
|------|------|
| `SOUL.md` | Persona, scope, boundaries |
| `SECURITY.md` | Secrets, external actions |
| `ESCALATION.md` | When to ask Boss / hand off |
| `USER.md` | Boss context |
| `BOOT.md` | Session startup reads (incl. `OBSIDIAN.md`) |
| `WORKFLOWS.md` | Domain workflows |
| `DATABASE.md` | Postgres scope for that agent |
| `OBSIDIAN.md` | Vault path + write rules |
| `memory/YYYY-MM-DD.md` | Daily session notes |
| `notes/`, `projects/` | Scratch and project work |

**Not yet standardized:** a single **“promote to Obsidian”** tool/workflow every agent must run after completing research or email triage.

---

## 6. Gmail — current vs target

### Today (implemented)

```text
clawsums@gmail.com
    → gmail-sync.py (every 15 min)
    → ops.emails (body, headers, domain_guess keyword)
    → processing_status = pending (no LLM step)
    → 7am report lists pending subjects
    → gog skill: agents can search mail in chat (OpenClaw)
```

**Gap:** No **analysis**, **extraction**, **task creation**, **Obsidian brief**, or **research queue**.

### Target pipeline (recommended)

```text
1. INGEST     gmail-sync.py          → ops.emails (unchanged)
2. CLASSIFY   LangGraph or admin job  → LLM reads body_text
3. EXTRACT    structured JSON        → entities, dates, URLs, people, intent
4. DECIDE     rules + model          → see decision matrix below
5. ACT        executors              → Paperclip API, Obsidian write, ArcadeDB upsert
6. NOTIFY     admin / Boss           → Telegram summary, action_required flag
```

### Email decision matrix (proposed)

| Signal | Action | Stores |
|--------|--------|--------|
| Clear task / deadline / “please fix” | Create **Paperclip** task → assign domain agent | `ops.emails.paperclip_issue_id`, Boss UI |
| FYI / newsletter / receipt | **Archive** or `informational` | Postgres status; optional one-line Obsidian in `Admin/Inbox/` |
| Needs research / comparison / “what do you think?” | **Paperclip** task → `research` + brief template in `Research/` | Obsidian + Postgres link |
| RE address / deal / comp language | Route → `realestate`; link RE graph when ArcadeDB ready | `domain_guess`, `assigned_agent` |
| GHL / CRM / pipeline language | Route → `ghl` | same |
| Duplicate / thread continuation | Link `thread_id`; don’t duplicate tasks | Postgres |
| Spam / marketing | `ignored` | Postgres only |
| High-risk external action | **Never auto-send**; `action_required` + Boss approval | ESCALATION policy |

### Schema already supports triage

`ops.emails` columns ready for pipeline: `processing_status`, `triage_notes`, `paperclip_issue_id`, `assigned_agent`, `domain_guess`.

**Implementer:** `scripts/gmail-triage.py` or **LangGraph graph `gmail_triage`** updating these fields.

---

## 7. LangGraph — what exists and what you still need

### Exists

- `docker-compose.yml` service `langgraph` (image `langchain/langgraph-api:latest`, port `8123`, `DATABASE_URI` to Postgres)
- Profile: `orchestration` (same as Paperclip)
- **Not** in `docker ps` today — service not started

### Still needed

| Item | Description |
|------|-------------|
| **LangGraph project package** | Python graphs in repo (e.g. `deploy/langgraph/`) versioned and mounted |
| **Graph: `gmail_triage`** | ingest pending emails → classify → update Postgres → optional Paperclip create |
| **Graph: `research_brief`** | URL/sources → summary → `Research/` Obsidian + Postgres metadata |
| **Graph: `scrape_validate_store`** | Bright Data webhook → validate → Postgres staging → notify `data` |
| **Graph: `daily_report_build`** | Optional: move heavy report assembly off cron script |
| **API auth** | LangSmith or internal token; OpenClaw agents call via HTTP tool |
| **Deploy** | `docker compose --profile orchestration up -d langgraph` + health check |
| **Observability** | Traces in Grafana or LangSmith; link from Paperclip task runs |

### Suggested trigger pattern

| Trigger | Graph |
|---------|--------|
| Cron after gmail-sync | `gmail_triage` (batch pending) |
| Paperclip task label `run:research-brief` | `research_brief` |
| Webhook from Bright Data | `scrape_validate_store` |
| Manual / admin Telegram | `invoke` with parameters |

OpenClaw **data** and **research** agents get a **tool** or instruction: “start LangGraph run X with payload Y.”

---

## 8. ArcadeDB — what you still need

| Item | Priority |
|------|----------|
| Document types: `Listing`, `Comp`, `Contact`, `Source`, `DocumentChunk` | High for RE + research |
| ETL from Postgres `realestate.*` → vertices/edges | High |
| Embedding pipeline (data agent) → vector index | Medium |
| Research RAG: chunk Obsidian/URLs → ArcadeDB | Medium |
| GHL relationship graph | Lower |
| 3D graph visualizer UI | Future (see §11) |

See [DATA-ARCADEDB-VS-POSTGRES.md](./DATA-ARCADEDB-VS-POSTGRES.md).

---

## 9. MinIO and self-hosted Supabase (recommendations)

Today the stack has **no S3-compatible object store** and **no Supabase**. Postgres holds text/metadata only; large binaries do not belong in `body_text` or BYTEA columns at scale.

### Where each fits in the Clawsum model

```text
                         ┌─────────────┐
                         │    Boss     │
                         └──────┬──────┘
                                │
     ┌──────────────────────────┼──────────────────────────┐
     ▼                          ▼                          ▼
 Obsidian (.md)            PostgreSQL (rows)            MinIO (blobs)
 human knowledge           system of record             files & media
     │                          │                          │
     │                    ArcadeDB (graph/vector)            │
     │                          │                          │
     └──────────────────────────┴──────────────────────────┘
                                │
                    Supabase (OPTIONAL layer)
                    auth · storage API · realtime · studio
                    sits ON TOP of Postgres + MinIO — not a 4th brain
```

| Layer | Keep / add | Role |
|-------|------------|------|
| **PostgreSQL** (current) | **Keep** | Emails, CRM, deals, triage state, scrape metadata, pointers to objects |
| **MinIO** | **Add (recommended)** | Attachments, PDFs, images, raw scrape ZIPs, exports, backups |
| **Supabase (self-hosted)** | **Defer or partial** | Boss/custom portal, Storage API, Auth — **do not** rip out Paperclip + raw Postgres without a plan |
| **Obsidian** | **Keep** | Narrative knowledge — not a blob store |
| **ArcadeDB** | **Keep** | Vectors/graph — not file storage |

---

### MinIO — **recommended (Wave 2)**

**Verdict:** Add MinIO **before** full Supabase. It solves a real gap Postgres was never meant to fill.

#### Good uses for Clawsum

| Bucket (example) | Contents | Written by | Postgres pointer |
|------------------|----------|------------|------------------|
| `clawsum-gmail` | MIME parts, PDFs, images from `ops.emails` | `gmail-sync` / triage | `ops.emails.attachments JSONB` → `{key, mime, size}` |
| `clawsum-scrapes` | Bright Data raw HTML/JSON/ZIP | `data` / LangGraph | `data.scrape_runs.object_prefix` |
| `clawsum-research` | Downloaded reports, large PDFs | `research` | `research.sources.object_key` |
| `clawsum-realestate` | Photos, plat maps, exports | `realestate` | listing/deal FK + key |
| `clawsum-exports` | CSV/Parquet snapshots for Boss | `data` | job metadata only |
| `clawsum-backups` | `pg_dump`, Obsidian tarballs | cron | none (ops only) |

#### Design rules

1. **Postgres stores metadata and S3 keys** — not multi-MB payloads.  
2. **Obsidian stays markdown** — link to MinIO URLs in frontmatter if needed (`attachment: s3://…`).  
3. **Agents access blobs** via presigned URLs or a thin internal API (LangGraph / `data` agent tool).  
4. **Bind MinIO to `127.0.0.1:9000`** (API) and `:9001` (console); expose console only via Traefik + auth if needed.  
5. **Same VPS disk** — plan volume size; lifecycle rules for old scrapes.

#### Compose sketch (when you add it)

```yaml
# profile: storage
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  volumes:
    - ./data/minio:/data
  ports:
    - "127.0.0.1:9000:9000"
    - "127.0.0.1:9001:9001"
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
```

Optional: **Supabase Storage** can use MinIO as its backend later (S3-compatible).

#### MinIO todos

- [ ] Add MinIO to `docker-compose.yml` (`storage` profile)  
- [ ] Create buckets + IAM-style access keys in `.env`  
- [ ] Extend `gmail-sync.py` to fetch/store attachments → keys in `ops.emails`  
- [ ] Backup cron: nightly `pg_dump` + Obsidian sync → `clawsum-backups`  

---

### Self-hosted Supabase — **defer full stack; consider partial later**

**Verdict:** You **already have** the core of what Supabase provides for *agents*:

| Supabase feature | Clawsum already has |
|------------------|---------------------|
| SQL database | **Postgres 16** (`clawsum`, `realestate`, `ghl`) |
| Auth | Paperclip Better Auth; OpenClaw gateway token; Telegram |
| REST/GraphQL API | Paperclip API; direct SQL from crons/LangGraph |
| Realtime | Not required for agents; optional for future Boss dashboard |
| Storage | **Use MinIO first**; Supabase Storage is optional wrapper |
| Studio | pgAdmin / `psql` / Grafana; Supabase Studio is nice-to-have |
| Edge Functions | LangGraph or small Python services on VPS |

A **full self-hosted Supabase** deploy (Kong, GoTrue, PostgREST, Realtime, Storage, Studio, etc.) adds **operational weight** (~8–12 containers) and **overlap** with Paperclip + raw Postgres. **Do not migrate** the agent stack to Supabase in Wave 1.

#### When Supabase *is* worth it

| Scenario | Use Supabase for |
|----------|------------------|
| Custom **Boss mission-control** web app (beyond Paperclip UI) | Auth (Google/OAuth), RLS per Boss user, Realtime inbox |
| Mobile-friendly **portal** for approvals | Row Level Security on shared tables |
| **Unified file picker** for non-technical users | Storage API over MinIO backend |
| Webhooks surface for partners | Edge Functions (or keep LangGraph) |

#### Three adoption paths (pick one later)

| Path | Effort | Fit for Clawsum |
|------|--------|-----------------|
| **A — MinIO only** | Low | **Best now** — blobs without platform churn |
| **B — Supabase Storage only** | Medium | MinIO backend + Supabase Storage API; keep existing Postgres service |
| **C — Full Supabase Postgres** | High | Migrate DB to Supabase’s Postgres; repoint LangGraph/Paperclip; use Realtime + Studio — only if building a large custom UI |
| **D — Defer** | None | Stay on Paperclip + Postgres until Boss portal requirements are written |

**Recommendation:** **Path A now**, re-evaluate **Path B** when Gmail attachments and scrapers produce large files, consider **Path C** only if Paperclip is insufficient for Boss UX.

#### If you self-host Supabase later

1. Run Supabase on a **separate compose profile** (`supabase`), not mixed into `clawsum` network without planning.  
2. Point Supabase at **either**:
   - its **own** Postgres (isolated) — for a new Boss app only, **or**
   - **external** connection to existing `clawsum` DB (advanced; schema `auth`, `storage` separation required).  
3. Configure **Storage** to use **MinIO** (`S3_ENDPOINT`, path-style) so you do not store files twice.  
4. Do **not** duplicate Gmail email bodies in Supabase tables — keep `ops.emails` canonical.  
5. Traefik routes: `supabase.*` Studio (IP-restricted), API only if needed.

Official reference: [Supabase self-hosting](https://supabase.com/docs/guides/self-hosting/docker).

#### Supabase todos (deferred)

- [ ] Write requirements for “Boss portal beyond Paperclip” (if any)  
- [ ] POC: self-hosted Supabase + MinIO backend on staging subdomain  
- [ ] Decision: Path A vs B vs C (see table above)  
- [ ] If Path C: migration plan for `clawsum` / `realestate` / `ghl` schemas  

---

### Updated four-store + objects model (target)

| Type | Store | Example |
|------|-------|---------|
| Structured facts | Postgres | `ops.emails.processing_status` |
| Large/binary | MinIO | Gmail PDF attachment |
| Narrative | Obsidian | Triage summary for Boss |
| Relationships / similarity | ArcadeDB | Comp ↔ listing edges |
| Optional app layer | Supabase | Boss portal auth + realtime (future) |

**Hermes / LangGraph:** write blobs to MinIO, summaries to Obsidian, rows to Postgres, graph upserts to ArcadeDB — same as OpenClaw agents.

---

### Resource note (single VPS)

Running **Clawsum + MinIO + full Supabase + ArcadeDB** on one HVPS is feasible but RAM-sensitive. Suggested order:

1. Current stack (as now)  
2. **+ MinIO** (~512 MB–1 GB baseline)  
3. **+ LangGraph**  
4. **+ Supabase** only after RAM check (`free -h`) and profile-based `docker compose` so unused profiles stay off  

---

## 10. UIs and dashboards

| Surface | Purpose | Status |
|---------|---------|--------|
| **Telegram** | Real-time chat, groups per agent | ✅ Clawsum |
| **Boss UI (Paperclip)** | Tasks, approvals, heartbeats, cost | ✅ localhost:3100 |
| **OpenClaw Control UI** | Gateway, channels, Gmail, devices | ✅ HTTPS Traefik |
| **Grafana** | Infra health, probes | ✅ |
| **Prometheus** | Metrics | ✅ |
| **7am global report** | Boss digest | ✅ Telegram + Obsidian |
| **Boss UI public URL** | No SSH | 📄 Doc only |
| **Unified “mission control”** | Single pane all agents + graphs | ⬜ Future |

Grafana does **not** replace Boss UI. Use both.

---

## 11. Voice and 3D visualizers (not started)

### Two-way voice (vision)

| Piece | Notes |
|-------|--------|
| **Input** | Telegram voice notes (existing channel), or web/mobile client |
| **STT** | OpenClaw / provider plugin |
| **Routing** | Same as text → `admin` or domain agent |
| **TTS reply** | Comms or admin with Boss-approved voice policy |
| **“Talk to the whole system”** | Requires **orchestrator** (admin + Paperclip): one voice session, admin delegates tasks |

**Not in compose or docs as implemented.** Treat as **Phase 9+**.

### 3D visualizers (vision)

| Use case | Tech direction |
|----------|----------------|
| RE comp graph | ArcadeDB export → Three.js / force-graph web view |
| System health | Grafana (2D) sufficient for ops |
| Agent activity | Paperclip + future OpenClaw metrics |
**Not started.** Depends on ArcadeDB population first.

---

## 12. Hermes + Paperclip + OpenClaw interaction

```text
Boss creates task in Paperclip
    → heartbeat assigns OpenClaw agent OR Hermes (long job)
    → OpenClaw: Telegram + tools + Postgres/Obsidian
    → Hermes: CLI in Paperclip container, multi-step autonomy
    → Result written to task + Obsidian + Postgres as appropriate
```

**Hermes and Obsidian:** Configure Paperclip/Hermes job templates to always write a markdown deliverable under `obsidian/<Agent>/` or `Paperclip/Runs/`.

---

## 13. Master system checklist (your full vision)

| Capability | Designed | Built | Next step |
|------------|----------|-------|-----------|
| 10 workers (9 OC + Hermes) | ✅ | ✅ Paperclip wired | Keep heartbeats healthy |
| OpenClaw multi-agent | ✅ | ✅ | Smoke-test all groups |
| Paperclip orchestration | ✅ | ✅ | Public Boss UI domain |
| Postgres per domain | ✅ | ✅ schemas | Populate + GHL API |
| Obsidian knowledge | ✅ | ✅ vault seed | Desktop sync + triage notes |
| ArcadeDB graph/RAG | ✅ | ⬜ empty | RE comp schema + ETL |
| Gmail archive | ✅ | ✅ | **Intelligent triage** |
| Gmail → tasks/knowledge | ✅ | ⬜ | LangGraph or `gmail-triage` |
| LangGraph workflows | ✅ | ⬜ | Package + 3 graphs |
| Bright Data scrapers | ✅ | ⬜ | Phase 5 |
| Monitoring | ✅ | ✅ | Alerting rules |
| Self-healing | ✅ | ⬜ | Phase 6 |
| AI Persona OS | ✅ | ✅ | Enforce Obsidian promotion |
| 2-way voice | ✅ | ⬜ | Phase 9+ |
| 3D visualization | ✅ | ⬜ | After ArcadeDB |
| Hostinger decommission | ✅ | 🔄 | Phase 8 cleanup |
| **MinIO object storage** | ✅ | ⬜ | Wave 2 — buckets + Gmail attachments |
| **Self-hosted Supabase** | Optional | ⬜ | Defer until Boss portal requirements |
| **Multi-VPS template** | ✅ Designed | 🔄 Tier 1+2 incomplete | [PLATFORM-DEPLOY-TEMPLATE.md](./PLATFORM-DEPLOY-TEMPLATE.md) — gate before clone |

---

## 14. Recommended build order (next 90 days)

### Wave 1 — Operational truth (2–3 weeks)

1. **Gmail triage pipeline** — LLM batch on `pending` → Paperclip tasks + status updates  
2. **Boss Obsidian sync** — git or Syncthing for your PC  
3. **Boss UI HTTPS** — `boss.*` Traefik + `PAPERCLIP_PUBLIC_URL`  
4. **Telegram smoke test** — all 9 groups  
5. **Admin playbook** — one page in `Admin/Runbooks/` for daily Boss routine  

### Wave 2 — Automation spine (3–5 weeks)

6. **MinIO** deploy + buckets + attachment fields on `ops.emails`  
7. **LangGraph deploy** + `gmail_triage` + `research_brief`  
8. **ArcadeDB RE comp schema** + first ETL from Postgres  
9. **GHL MCP / API** wiring (Phase 7)  
10. **Bright Data** scrape → Postgres + MinIO raw blobs (Phase 5)  

### Wave 3 — Boss experience (ongoing)

11. Real-time Gmail (gog hooks) optional  
12. Grafana alerts → Telegram admin  
13. ArcadeDB → simple graph viewer  
14. **Supabase POC** (only if custom Boss portal spec exists) — Storage on MinIO backend  
15. Voice experiment on admin DM  
16. Decommission Hostinger paths  

---

## 15. Todo list (actionable)

### Critical

- [ ] **Gmail intelligent triage** — `gmail-triage.py` or LangGraph; populate `processing_status`, `paperclip_issue_id`, `triage_notes`
- [ ] **Boss Obsidian desktop access** — choose git / Syncthing / SSHFS; open vault
- [ ] **Document Boss daily routine** — Boss UI → Telegram → `Admin/Reports/` → pending emails

### LangGraph

- [ ] Create `deploy/langgraph/` package (graphs + `langgraph.json`)
- [ ] Start service: `docker compose --profile orchestration up -d langgraph`
- [ ] Implement **`gmail_triage`** graph (Postgres in/out)
- [ ] Implement **`research_brief`** graph (Obsidian `Research/` out)
- [ ] Expose invoke URL/token to **data** and **admin** agents (tool config)

### Obsidian + knowledge

- [ ] Policy: every research deliverable → `Research/Briefs/YYYY-MM-DD-slug.md`
- [ ] Hermes job template → markdown under `Paperclip/` or assignee folder
- [ ] Optional: `Admin/Inbox/YYYY-MM-DD.md` auto-generated from triage cron
- [ ] Disable or archive **hhmail** skill confusion (Hostinger IMAP) — gog is canonical for Gmail

### ArcadeDB

- [ ] Run `arcadedb-ingest.py` from RE/Research ETL (schema-on-arrival — see DATA-ARCADEDB doc)
- [ ] Define graph schema for RE comps
- [ ] ETL script: Postgres `realestate` → ArcadeDB JSONL → ingest
- [ ] Research chunk ingestion (URLs → vector)

### MinIO (recommended Wave 2)

- [ ] Add MinIO service + `data/minio` volume + `.env` credentials  
- [ ] Schema: `ops.emails.attachments` JSONB (or new table `ops.email_attachments`)  
- [ ] `gmail-sync.py`: store parts → MinIO, save keys  
- [ ] Scraper pipeline: raw artifacts → `clawsum-scrapes`  
- [ ] Nightly backup job → `clawsum-backups`  

### Supabase (defer)

- [ ] Document whether Boss needs a portal beyond Paperclip  
- [ ] If yes: POC self-hosted Supabase with MinIO as Storage backend (Path B)  
- [ ] Do **not** replace existing Postgres until Path C is explicitly approved  

### Platform / UI

- [ ] Boss UI public domain (see [BOSS-UI-PUBLIC-DOMAIN.md](./BOSS-UI-PUBLIC-DOMAIN.md))
- [ ] Phase 8: remove Hostinger stack from disk after backup
- [ ] Prometheus alert rules → Telegram
- [ ] Fix any remaining agent `EACCES` session paths (comms)

### Future (voice / 3D)

- [ ] Voice: STT/TTS policy in `admin` + `comms` SOUL
- [ ] 3D: export ArcadeDB subgraph for web viewer
- [ ] Unified mission-control dashboard (optional Grafana + custom panel)

---

## 16. Related docs

| Doc | Topic |
|-----|--------|
| [PLATFORM-DEPLOY-TEMPLATE.md](./PLATFORM-DEPLOY-TEMPLATE.md) | **Multi-VPS template gate**, tiers, bootstrap, instance checklist |
| [GHL-MULTI-ACCOUNT-PLAN.md](./GHL-MULTI-ACCOUNT-PLAN.md) | Per-account GHL agents (MCO/AVE/WNN REI), MCP, template |
| [BOSS-OBSIDIAN-WINDOWS.md](./BOSS-OBSIDIAN-WINDOWS.md) | Obsidian vault on Boss PC (SSHFS) |
| [VERSION-PINNING.md](./VERSION-PINNING.md) | OpenClaw / Paperclip / Hermes — deployed vs latest stable |
| [SETUP-REMAINING.md](./SETUP-REMAINING.md) | **What’s done vs left** — Boss queue vs platform checklist; why Boss UI errors happen |
| [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md) | Phases 0–8 |
| [OBSIDIAN-VAULT.md](./OBSIDIAN-VAULT.md) | Vault layout, sync |
| [DATA-ARCADEDB-VS-POSTGRES.md](./DATA-ARCADEDB-VS-POSTGRES.md) | Data placement |
| [GMAIL-ADMIN-SETUP.md](./GMAIL-ADMIN-SETUP.md) | OAuth, sync, gog |
| [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) | Boss UI vs Grafana |
| [PAPERCLIP-SETUP.md](./PAPERCLIP-SETUP.md) | Agents, Hermes, gateway |
| [BOSS-ACCESS-GUIDE.md](./BOSS-ACCESS-GUIDE.md) | Every Boss UI URL, SSH tunnel, LLM billing |
| [OPENAI-AUTH.md](./OPENAI-AUTH.md) | Codex vs API key |

---

## 17. One-paragraph answers to your direct questions

**Obsidian for all agents including Hermes?**  
Yes by design: nine OpenClaw workspaces + `Paperclip/` for orchestration/Hermes deliverables. Hermes has no separate workspace; its output must be **written into** Obsidian and Paperclip explicitly.

**Should Boss manage Obsidian?**  
Boss should **read the whole vault**, **write mainly in `Admin/`**, and **delegate** domain content to agents via Paperclip — not edit `RealEstate/` or `GHL/` routinely.

**LangGraph?**  
Compose stub only; need Python graphs, deploy service, and three workflows minimum (Gmail triage, research brief, scrape pipeline).

**Gmail processing?**  
Ingest works; **analysis and decisions are not built** — highest-value next automation.

**Master system (voice, 3D, full integration)?**  
Core orchestration is **live**; knowledge automation and LangGraph are the gap; voice and 3D are **future phases** after Postgres/Obsidian/ArcadeDB pipelines exist.

**MinIO?**  
**Yes, add it** for Gmail attachments, scraper blobs, exports, and backups. Postgres keeps pointers; Obsidian keeps prose.

**Self-hosted Supabase?**  
**Not required** for the 10-agent + Paperclip stack today. **Defer** full Supabase; use **MinIO first**. Revisit Supabase when you want a custom Boss portal (auth, realtime, Storage API) on top of the same Postgres/MinIO — not as a replacement for Paperclip.

---

*This report reflects the repository and VPS state as of 2026-05-23. Re-run `python3 /docker/clawsum/scripts/setup-obsidian-vault.py --sync-only` and check `docker ps` after any deploy change.*
