# Clawsum Platform — Implementation Plan

**Server:** `srv.example.com` (`YOUR_VPS_IP`)  
**Current:** Hostinger HVPS OpenClaw `2026.5.7` at `/docker/openclaw-qpr7/`  
**Target:** Self-managed stack at `/docker/clawsum/`

---

## Locked decisions (Boss — May 21, 2026)

| Decision | Choice |
|----------|--------|
| **OpenClaw version** | **`2026.6.10`** — pinned in compose + `.env`; see [VERSION-PINNING.md](deploy/docs/VERSION-PINNING.md) |
| **Orchestrator** | **Paperclip** — task routing across all agents; **admin** OpenClaw agent = Telegram front door + Paperclip liaison |
| **Telegram** | **Separate group per agent** (not forum topics) |
| **WhatsApp** | **comms agent only** — not global, not Hostinger auto-install |
| **GHL vs Real Estate** | **Separate agents** — overlap via shared Postgres/ArcadeDB, not merged workspaces |
| **Include now** | LangGraph, Paperclip, Hermes, ArcadeDB, Obsidian, Postgres — per domain where applicable |

---

## Version

| Item | Value |
|------|--------|
| Install image | `ghcr.io/openclaw/openclaw:2026.6.10` |
| Staging port | `48166` (Hostinger stays on `48165` until cutover) |
| Upgrade policy | Pin tag; test on staging; you approve bumps |

---

## Architecture

```
Boss
 ├── Telegram DM ──────────────► admin (OpenClaw) ◄──► Paperclip (orchestrator)
 ├── TG Group: Clawsum Coding ──► coding
 ├── TG Group: Clawsum Data ────► data
 ├── TG Group: Clawsum RE ──────► realestate
 ├── TG Group: Clawsum GHL ─────► ghl
 ├── TG Group: Clawsum Comms ───► comms (+ WhatsApp)
 ├── TG Group: Clawsum Research ► research
 ├── TG Group: Clawsum Planning ► planning
 └── TG Group: Clawsum Ops ─────► admin (reports)

Paperclip ──assigns──► OpenClaw agents | Hermes (long jobs)
LangGraph ──workflows──► data / research / scraper pipelines

Shared platform (Docker network `clawsum`):
  postgres (schemas per domain)
  arcadedb (graph/vector — RE, research, GHL)
  obsidian vault mount (per-agent folders)
  prometheus + grafana
  paperclip :3100
  langgraph-api (phase 1 placeholder / service TBD)
```

**Rule:** `1 domain = 1 agent = 1 workspace` (+ shared DB schemas, not shared MEMORY.md)

---

## Agent roster (final)

| Agent | Workspace | Telegram | WhatsApp | Postgres | Obsidian folder |
|-------|-----------|----------|----------|----------|-----------------|
| `admin` | `workspace-admin` | DM + Ops group | — | DB `clawsum` schema `ops` | `Admin/` |
| `coding` | `workspace-coding` | Coding group | — | DB `clawsum` schema `coding` | `Coding/` |
| `data` | `workspace-data` | Data group | — | DB `clawsum` schema `data` | `Data/` |
| `realestate` | `workspace-realestate` | RE group | — | **DB `realestate`** (isolated) | `RealEstate/` |
| `ghl` | `workspace-ghl` | GHL group | — | **DB `ghl`** (isolated) | `GHL/` |
| `comms` | `workspace-comms` | Comms group | **yes** | `comms` | `Comms/` |
| `research` | `workspace-research` | Research group | — | `research` | `Research/` |
| `planning` | `workspace-planning` | Planning group | — | `planning` | `Planning/` |

Hermes: invoked by Paperclip for long jobs — not a Telegram-facing agent.

---

## GHL ↔ Real Estate crossover

- **Separate agents, separate MEMORY.md and SOUL.md**
- **Separate Postgres databases:** `realestate` and `ghl` — no cross-DB queries
- Crossover only via **Paperclip tasks**, **data agent ETL**, or Boss-approved exports
- **ESCALATION.md** on each: when to hand off to the other agent
- Admin does not own domain data — routes only

---

## Multi-VPS template gate

**Do not deploy additional unrelated VPS instances until the template is complete.**

See **[deploy/docs/PLATFORM-DEPLOY-TEMPLATE.md](deploy/docs/PLATFORM-DEPLOY-TEMPLATE.md)** — Tier 0/1/2 completion gates, greenfield bootstrap, instance overlay checklist.

---

## Phase status

| Phase | Status |
|-------|--------|
| 0 Decisions | ✅ Done |
| 1 Self-hosted OpenClaw + platform compose | ✅ Done (48166 staging) |
| 2 Migration from Hostinger | ✅ Done |
| 3 Multi-agent + Telegram bindings | ✅ Done (9 groups incl. Paperclip) |
| 3b AI Persona OS per workspace | ✅ Done (SOUL/SECURITY/ESCALATION seeded) |
| 4 Postgres + ArcadeDB + Obsidian per domain | 🔄 Postgres + Obsidian done; ArcadeDB empty |
| 5 Scrapers (Bright Data) | ⬜ Tier 2 / optional pack |
| 6 Monitoring + daily reports + self-healing | 🔄 Monitoring up; Grafana→Telegram alerts pending |
| 7 LangGraph + Paperclip + Hermes integration | 🔄 Paperclip live; LangGraph stub only |
| 8 Cutover + decommission Hostinger | 🔄 Telegram cut over; disk cleanup pending |
| **Template complete (Tier 1+2)** | ⬜ **Blocks additional VPS** — see PLATFORM-DEPLOY-TEMPLATE.md |

---

## Migration source (Hostinger)

| Asset | From |
|-------|------|
| Workspaces | `/docker/openclaw-qpr7/data/.openclaw/workspace*` |
| State | `/docker/openclaw-qpr7/data/.openclaw/` |
| Secrets | `/docker/openclaw-qpr7/.env` → `/docker/clawsum/.env` |

**Do not migrate:** `/hostinger/server.mjs` bootstrap.

---

## LangGraph placement

- Python service on `clawsum` Docker network
- Workflows: scrape→validate→store, research brief, daily report build
- OpenClaw **data** / **research** agents trigger graphs; graphs write to Postgres + Obsidian

---

## References

- **[PLATFORM-DEPLOY-TEMPLATE.md](deploy/docs/PLATFORM-DEPLOY-TEMPLATE.md)** — **multi-VPS template gate**, Tier 0–3, bootstrap, finish order
- **[PLATFORM-MASTER-REPORT.md](deploy/docs/PLATFORM-MASTER-REPORT.md)** — full stack status, knowledge model, Gmail/LangGraph roadmap, Boss + Obsidian roles, todo list
- **[BOSS-ACCESS-GUIDE.md](deploy/docs/BOSS-ACCESS-GUIDE.md)** — how Boss opens Telegram, Boss UI, Control UI, Grafana, ArcadeDB, Gmail, LLM billing
- [OpenClaw v2026.5.20](https://github.com/openclaw/openclaw/releases/tag/v2026.5.20)
- [OpenClaw Docker](https://docs.openclaw.ai/install/docker)
- [Paperclip Docker](https://paperclip.inc/docs/deploy/docker)
- [Multi-agent routing](https://docs.openclaw.ai/concepts/multi-agent)
